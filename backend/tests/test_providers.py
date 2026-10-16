from enum import StrEnum

import pytest
from pydantic import BaseModel, Field

from app.providers.base import ProviderError, ProviderOutputError
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


def test_mock_instance_fills_nested_schema():
    obj = mock_instance(Outer)
    assert obj.inner.title == "[mock] 제목"
    assert len(obj.items) == 1
    assert obj.kind is Kind.FIRST
    assert obj.tags and obj.tags[0].startswith("[mock]")
    assert obj.note is not None and obj.note.startswith("[mock]")


def test_mock_provider_returns_parsed_and_records_call():
    provider = MockProvider()
    response = provider.complete(task_type="t", stage="generate", prompt="hello", response_model=Inner)
    assert isinstance(response.parsed, Inner)
    assert response.model == "mock"
    assert response.usage.input_tokens == 5
    assert provider.calls == [("t", "generate")]


def test_mock_provider_without_model_returns_text():
    response = MockProvider().complete(task_type="t", stage="diagnose", prompt="p")
    assert response.parsed is None
    assert response.text == "[mock] diagnose"


def test_mock_provider_failure_modes():
    with pytest.raises(ProviderError):
        MockProvider(fail_stages={"generate"}).complete(task_type="t", stage="generate", prompt="p")

    provider = MockProvider(output_errors={"generate": 1})
    with pytest.raises(ProviderOutputError):
        provider.complete(task_type="t", stage="generate", prompt="p", response_model=Inner)
    assert provider.complete(task_type="t", stage="generate", prompt="p", response_model=Inner).parsed


def test_get_provider():
    assert get_provider("mock").name == "mock"
    with pytest.raises(ValueError):
        get_provider("claude")
