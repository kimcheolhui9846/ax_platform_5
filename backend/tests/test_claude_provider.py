"""ClaudeProvider: 네트워크 없이 요청 모양과 결과·오류 변환을 확인한다(돈을 쓰지 않는다).

응답 처리는 실제 SDK 클라이언트에 httpx2 MockTransport를 꽂아 확인한다(SDK가 응답을 읽는 방식까지 지나간다).
SDK 예외 변환은 가짜 클라이언트로 확인한다.
"""
import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx  # anthropic 1.x는 httpx2를 쓴다
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderError, ProviderOutputError
from app.providers.claude import FALLBACK_BETA, ClaudeProvider


class Answer(BaseModel):
    text: str


PROMPT = Prompt(system="고정된 과제 설명", user="세션 맥락")


class Server:
    """Messages API 흉내. 받은 요청을 모두 남기고 정해 둔 응답 하나를 돌려준다."""

    def __init__(self, content, stop_reason="end_turn"):
        self.content, self.stop_reason, self.requests = content, stop_reason, []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-5-5",
                "content": self.content,
                "stop_reason": self.stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 120, "output_tokens": 30},
            },
        )

    @property
    def body(self) -> dict:
        [request] = self.requests
        return json.loads(request.content)


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def provider_for(server: Server, model: str = "claude-opus-5-5", effort: str = "medium") -> ClaudeProvider:
    client = anthropic.Anthropic(
        api_key="test-key", http_client=httpx.Client(transport=httpx.MockTransport(server)), max_retries=0
    )
    return ClaudeProvider(model=model, effort=effort, client=client)


def complete(provider: ClaudeProvider, response_model=Answer):
    return provider.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=response_model)


def test_sends_the_request_shape_and_parses_the_answer():
    server = Server([text('{"text": "안녕"}')])

    response = complete(provider_for(server))

    body = server.body
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 16000
    assert body["system"] == [{"type": "text", "text": "고정된 과제 설명", "cache_control": {"type": "ephemeral"}}]
    assert body["messages"] == [{"role": "user", "content": "세션 맥락"}]
    assert body["output_config"]["effort"] == "medium"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["output_config"]["format"]["schema"] == anthropic.transform_schema(Answer)
    assert body["fallbacks"] == "default"
    assert FALLBACK_BETA in server.requests[0].headers["anthropic-beta"]
    assert "thinking" not in body and "temperature" not in body
    assert response.parsed == Answer(text="안녕")
    assert (response.model, response.usage.input_tokens, response.usage.output_tokens) == ("claude-opus-5-5", 120, 30)


def test_refusal_is_a_call_failure_without_a_second_request():
    server = Server([text("I can't help with that.")], stop_reason="refusal")
    with pytest.raises(ProviderError) as caught:
        complete(provider_for(server))
    assert not isinstance(caught.value, ProviderOutputError)  # 다시 불러도 같으니 하네스가 다시 부르지 않게
    assert len(server.requests) == 1


def test_truncated_json_is_an_output_error():
    server = Server([text('{"text": "안')], stop_reason="max_tokens")
    with pytest.raises(ProviderOutputError, match="잘렸"):
        complete(provider_for(server))


def test_invalid_json_is_an_output_error():
    server = Server([text('{"other": 1}')])
    with pytest.raises(ProviderOutputError, match="스키마"):
        complete(provider_for(server))


def test_mid_output_fallback_parses_the_last_text_block():
    server = Server(
        [
            text('{"text": "앞'),
            {"type": "fallback", "from": {"model": "claude-opus-5-5"}, "to": {"model": "claude-opus-4-8"}},
            text('{"text": "완성"}'),
        ]
    )
    response = complete(provider_for(server))
    assert response.parsed == Answer(text="완성")
    assert response.text == '{"text": "완성"}'


def test_haiku_is_sent_without_fallbacks():
    server = Server([text('{"text": "x"}')])
    complete(provider_for(server, model="claude-haiku-5-5", effort="low"))
    assert "fallbacks" not in server.body
    assert FALLBACK_BETA not in server.requests[0].headers.get("anthropic-beta", "")


def test_without_a_response_model_returns_the_text():
    # response_model이 없으면 구조화 출력 없이 글만 받는다(하네스는 언제나 모델을 넘기지만 계약상 선택이다)
    server = Server([text("그냥 글")])
    response = complete(provider_for(server), response_model=None)
    assert "format" not in server.body["output_config"]
    assert server.body["fallbacks"] == "default"
    assert (response.text, response.parsed) == ("그냥 글", None)


def test_missing_api_key_fails_at_construction(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        ClaudeProvider(model="claude-opus-5-5", effort="medium")


class FailingMessages:
    def __init__(self, error):
        self.error = error

    def create(self, **kwargs):
        raise self.error


def api_errors():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return [
        anthropic.APIConnectionError(request=request),
        anthropic.APITimeoutError(request=request),
        anthropic.RateLimitError("rate", response=httpx.Response(429, request=request), body=None),
        anthropic.InternalServerError("boom", response=httpx.Response(500, request=request), body=None),
        anthropic.AuthenticationError("key", response=httpx.Response(401, request=request), body=None),
    ]


@pytest.mark.parametrize("error", api_errors())
def test_sdk_errors_become_provider_errors(error):
    client = SimpleNamespace(beta=SimpleNamespace(messages=FailingMessages(error)))
    provider = ClaudeProvider(model="m", effort="medium", client=client)
    with pytest.raises(ProviderError) as caught:
        complete(provider)
    assert not isinstance(caught.value, ProviderOutputError)
