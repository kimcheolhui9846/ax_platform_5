"""모델 제공자 인터페이스. 하네스는 이 인터페이스만 알고 실제 모델은 모른다."""
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ProviderResponse:
    text: str
    model: str
    parsed: BaseModel | None = None
    usage: Usage = field(default_factory=Usage)


class ProviderError(Exception):
    """모델 호출 자체가 실패했다 (네트워크, 인증, 한도 등)."""


class ProviderOutputError(ProviderError):
    """호출은 됐지만 응답이 요청한 스키마를 통과하지 못했다."""


class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse: ...
