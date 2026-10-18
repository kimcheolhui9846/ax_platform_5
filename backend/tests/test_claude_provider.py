"""ClaudeProvider: 실제 SDK 대신 가짜 클라이언트로 요청 모양과 결과·오류 변환을 확인한다(돈을 쓰지 않는다)."""
from types import SimpleNamespace

import anthropic
import httpx2 as httpx  # anthropic 1.x는 httpx2를 쓴다
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderError, ProviderOutputError
from app.providers.claude import ClaudeProvider


class Answer(BaseModel):
    text: str


class FakeMessages:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls, self.methods = result, error, [], []

    def parse(self, **kwargs):
        return self._call("parse", kwargs)

    def create(self, **kwargs):
        return self._call("create", kwargs)

    def _call(self, method, kwargs):
        self.methods.append(method)
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def fake_client(messages: FakeMessages):
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def message(parsed=None, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[SimpleNamespace(type="text", text='{"text": "안녕"}')],
        usage=SimpleNamespace(input_tokens=120, output_tokens=30),
    )


PROMPT = Prompt(system="고정된 과제 설명", user="세션 맥락")


def test_sends_system_as_a_cached_block_and_user_as_the_message():
    messages = FakeMessages(result=message(Answer(text="안녕")))
    provider = ClaudeProvider(model="claude-opus-5-5", effort="medium", client=fake_client(messages))

    response = provider.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=Answer)

    assert messages.methods == ["parse"]
    [call] = messages.calls
    assert call["model"] == "claude-opus-5-5"
    assert call["system"] == [{"type": "text", "text": "고정된 과제 설명", "cache_control": {"type": "ephemeral"}}]
    assert call["messages"] == [{"role": "user", "content": "세션 맥락"}]
    assert call["output_format"] is Answer
    assert call["output_config"] == {"effort": "medium"}
    assert call["max_tokens"] == 16000
    assert "thinking" not in call and "temperature" not in call
    assert response.parsed == Answer(text="안녕")
    assert (response.model, response.usage.input_tokens, response.usage.output_tokens) == ("claude-opus-5-5", 120, 30)


def test_opts_into_server_side_fallbacks():
    messages = FakeMessages(result=message(Answer(text="x")))
    ClaudeProvider(model="claude-opus-5-5", effort="low", client=fake_client(messages)).complete(
        task_type="t", stage="diagnose", prompt=PROMPT, response_model=Answer
    )
    call = messages.calls[0]
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call.get("fallbacks", call.get("extra_body", {}).get("fallbacks")) == "default"


@pytest.mark.parametrize(
    ("result", "error_type"),
    [
        (message(None, "refusal"), ProviderError),
        (message(None, "max_tokens"), ProviderOutputError),
        (message(None, "end_turn"), ProviderOutputError),
    ],
)
def test_unusable_responses_become_provider_errors(result, error_type):
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(result=result)))
    with pytest.raises(error_type):
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)


def test_refusal_is_not_an_output_error():
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(result=message(None, "refusal"))))
    with pytest.raises(ProviderError) as caught:
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)
    assert not isinstance(caught.value, ProviderOutputError)  # 다시 불러도 같으니 한 번 더 부르지 않게


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
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(error=error)))
    with pytest.raises(ProviderError) as caught:
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)
    assert not isinstance(caught.value, ProviderOutputError)


def test_schema_validation_failures_become_output_errors():
    from pydantic import ValidationError

    try:
        Answer.model_validate({})
    except ValidationError as error:
        invalid = error
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(error=invalid)))
    with pytest.raises(ProviderOutputError):
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)


def test_without_a_response_model_returns_the_text():
    messages = FakeMessages(result=message(None))
    # response_model이 없으면 구조화 출력 없이 글만 받는다(하네스는 언제나 모델을 넘기지만 계약상 선택이다)
    provider = ClaudeProvider(model="claude-opus-5-5", effort="medium", client=fake_client(messages))

    response = provider.complete(task_type="t", stage="generate", prompt=PROMPT)

    assert messages.methods == ["create"]
    [call] = messages.calls
    assert "output_format" not in call
    assert call["system"][0]["text"] == "고정된 과제 설명"
    assert call["messages"] == [{"role": "user", "content": "세션 맥락"}]
    assert call["output_config"] == {"effort": "medium"}
    assert call["fallbacks"] == "default"
    assert (response.text, response.parsed) == ('{"text": "안녕"}', None)
