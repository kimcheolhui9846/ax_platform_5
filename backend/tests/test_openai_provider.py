"""OpenAIProvider: 네트워크 없이 요청 모양과 결과·오류 변환을 확인한다(돈을 쓰지 않는다).

실제 SDK 클라이언트에 httpx2 MockTransport를 꽂아 SDK가 응답을 읽는 방식까지 지나간다.
"""
import json
from typing import Generic, TypeVar

import httpx2 as httpx  # openai 3.x도 httpx2를 쓴다
import openai
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderError, ProviderOutputError
from app.providers.openai_chat import OpenAIProvider, response_format

T = TypeVar("T")


class Answer(BaseModel):
    text: str


class Wrapped(BaseModel, Generic[T]):
    value: T


PROMPT = Prompt(system="고정된 과제 설명", user="세션 맥락")


class Server:
    """Chat Completions 흉내. 받은 요청을 모두 남기고 정해 둔 응답 하나를 돌려준다."""

    def __init__(self, content, finish_reason="stop", usage=None, refusal=None, status=200):
        self.content, self.finish_reason, self.refusal, self.status = content, finish_reason, refusal, status
        self.usage = usage or {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150}
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "원문 오류", "type": "x"}})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_test",
                "object": "chat.completion",
                "created": 0,
                "model": "gpt-6.1-terra",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": self.finish_reason,
                        "message": {"role": "assistant", "content": self.content, "refusal": self.refusal},
                    }
                ],
                "usage": self.usage,
            },
        )

    @property
    def body(self) -> dict:
        [request] = self.requests
        return json.loads(request.content)


def provider_for(server: Server, model: str = "gpt-6.1-terra", effort: str = "medium") -> OpenAIProvider:
    client = openai.OpenAI(
        api_key="test-key", http_client=httpx.Client(transport=httpx.MockTransport(server)), max_retries=0
    )
    return OpenAIProvider(model=model, effort=effort, client=client)


def complete(provider: OpenAIProvider, response_model=Answer):
    return provider.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=response_model)


def test_sends_the_request_shape_and_parses_the_answer():
    server = Server('{"text": "안녕"}')
    response = complete(provider_for(server, effort="low"))

    body = server.body
    assert body["model"] == "gpt-6.1-terra"
    assert body["reasoning_effort"] == "low"
    assert body["messages"] == [
        {"role": "system", "content": "고정된 과제 설명"},
        {"role": "user", "content": "세션 맥락"},
    ]
    schema = body["response_format"]
    assert schema["type"] == "json_schema"
    assert schema["json_schema"]["strict"] is True
    assert schema["json_schema"]["schema"]["additionalProperties"] is False
    assert response.parsed == Answer(text="안녕")
    assert (response.text, response.model) == ('{"text": "안녕"}', "gpt-6.1-terra")
    assert (response.usage.input_tokens, response.usage.output_tokens) == (120, 30)


def test_generic_model_names_become_valid_schema_names():
    """제네릭 모델 이름(`Wrapped[Answer]`)의 대괄호는 OpenAI 스키마 이름 규칙을 어겨 400이 난다."""
    server = Server('{"value": {"text": "x"}}')
    complete(provider_for(server), response_model=Wrapped[Answer])
    name = server.body["response_format"]["json_schema"]["name"]
    assert name and all(ch.isalnum() or ch in "_-" for ch in name)


def test_cached_tokens_are_split_out_of_input():
    """OpenAI의 prompt_tokens는 캐시 읽기를 포함한다. 계약(Claude와 같게)은 캐시를 뺀 입력이다."""
    usage = {
        "prompt_tokens": 1000,
        "completion_tokens": 10,
        "total_tokens": 1010,
        "prompt_tokens_details": {"cached_tokens": 800},
    }
    response = complete(provider_for(Server('{"text": "x"}', usage=usage)))
    assert (response.usage.input_tokens, response.usage.cache_read_input_tokens) == (200, 800)
    assert response.usage.cache_creation_input_tokens == 0


def test_refusal_is_a_call_failure():
    with pytest.raises(ProviderError, match="거절") as caught:
        complete(provider_for(Server(None, refusal="I can't help with that.")))
    assert not isinstance(caught.value, ProviderOutputError)


def test_content_filter_is_a_call_failure():
    with pytest.raises(ProviderError) as caught:
        complete(provider_for(Server(None, finish_reason="content_filter")))
    assert not isinstance(caught.value, ProviderOutputError)


def test_truncated_json_is_an_output_error():
    with pytest.raises(ProviderOutputError, match="잘렸"):
        complete(provider_for(Server('{"text": "안', finish_reason="length")))


def test_invalid_json_is_an_output_error():
    with pytest.raises(ProviderOutputError, match="스키마"):
        complete(provider_for(Server('{"wrong": 1}')))


def test_without_a_response_model_returns_the_text():
    server = Server("그냥 글")
    response = complete(provider_for(server), response_model=None)
    assert "response_format" not in server.body
    assert (response.text, response.parsed) == ("그냥 글", None)


@pytest.mark.parametrize("status", [400, 401, 429, 500])
def test_sdk_errors_become_provider_errors_without_the_raw_message(status):
    with pytest.raises(ProviderError) as caught:
        complete(provider_for(Server(None, status=status)))
    assert not isinstance(caught.value, ProviderOutputError)
    assert "원문 오류" not in str(caught.value)


def test_endpoint_and_key_are_passed_to_the_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(
        model="gpt-6-luna", effort="low", base_url="https://gateway.example/v1/gateway", api_key="gw-key"
    )
    assert str(provider.client.base_url).rstrip("/") == "https://gateway.example/v1/gateway"
    assert provider.client.api_key == "gw-key"


def test_missing_api_key_fails_at_construction(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIProvider(model="gpt-6-luna", effort="low")


def harness_response_models():
    """하네스가 실제로 response_model로 넘기는 모델 전부: 단계 모델과 과제마다 결과(병렬 조각 포함)."""
    from app.harness import stage_models
    from app.harness.registry import TASK_TYPES, build_harness
    from app.providers.mock import MockProvider

    models = [stage_models.Diagnosis, stage_models.GeneratedQuestion, stage_models.ProposedValues, stage_models.LLMReview]
    for task in TASK_TYPES:
        harness = build_harness(task, MockProvider())
        models.append(harness.result_model)
        models.extend(harness.part_models.values())
    return models


@pytest.mark.parametrize("model", harness_response_models(), ids=lambda m: m.__name__)
def test_every_harness_model_has_a_strict_schema(model):
    """strict 변환이 안 되는 스키마는 실제 호출 때 400이 난다. 돈을 쓰기 전에 여기서 잡는다."""
    rf = response_format(model)
    assert rf["json_schema"]["schema"]["additionalProperties"] is False
