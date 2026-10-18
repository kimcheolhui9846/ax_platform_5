from enum import StrEnum

import pytest
from pydantic import BaseModel, Field

from app.providers.base import Prompt, ProviderError, ProviderOutputError
from app.providers.claude import ClaudeProvider
from app.providers.factory import get_provider
from app.providers.mock import MockProvider
from app.providers.mock_fill import mock_instance


class Kind(StrEnum):
    FIRST = "first"
    SECOND = "second"


class Inner(BaseModel):
    title: str = Field(description="제목")
    score: int


class Outer(BaseModel):
    name: str
    tags: list[str]
    inner: Inner
    items: list[Inner]
    kind: Kind
    note: str | None = None
    flag: bool


P = Prompt(system="s", user="p")


def test_mock_instance_fills_nested_schema():
    obj = mock_instance(Outer)
    assert obj.inner.title == "[mock] 제목"
    assert len(obj.items) == 1
    assert obj.kind is Kind.FIRST
    assert obj.tags and obj.tags[0].startswith("[mock]")
    assert obj.note is not None and obj.note.startswith("[mock]")


def test_mock_provider_returns_parsed_and_records_call():
    provider = MockProvider()
    response = provider.complete(
        task_type="t", stage="generate", prompt=Prompt(system="sys", user="hello"), response_model=Inner
    )
    assert isinstance(response.parsed, Inner)
    assert response.model == "mock"
    assert response.usage.input_tokens == 8
    assert provider.calls == [("t", "generate")]


def test_mock_provider_without_model_returns_text():
    response = MockProvider().complete(task_type="t", stage="diagnose", prompt=P)
    assert response.parsed is None
    assert response.text == "[mock] diagnose"


def test_mock_provider_failure_modes():
    with pytest.raises(ProviderError):
        MockProvider(fail_stages={"generate"}).complete(task_type="t", stage="generate", prompt=P)

    provider = MockProvider(output_errors={"generate": 1})
    with pytest.raises(ProviderOutputError):
        provider.complete(task_type="t", stage="generate", prompt=P, response_model=Inner)
    assert provider.complete(task_type="t", stage="generate", prompt=P, response_model=Inner).parsed


def test_get_provider():
    assert get_provider("mock").name == "mock"
    with pytest.raises(ValueError, match="claude"):
        get_provider("unknown")


def test_get_provider_builds_claude_without_calling(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")  # 생성만 한다. 실제 호출은 하지 않는다.
    provider = get_provider("claude", model="claude-haiku-5-5", effort="low")
    assert isinstance(provider, ClaudeProvider)
    assert (provider.name, provider.model, provider.effort) == ("claude", "claude-haiku-5-5", "low")
