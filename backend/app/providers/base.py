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
    """모델 어댑터 계약.

    complete()는 SDK 예외(네트워크·인증·한도·타임아웃 등)를 모두 ProviderError로, 응답을
    response_model로 파싱하지 못한 경우를 ProviderOutputError로 감싸서 던져야 한다. 감싸지 않은
    예외는 실패 trace가 남지 않고 502 대신 500으로 끝난다(생성 단계에서는 일반 실패로 뭉개진다).
    원문 오류 문구는 trace에만 남고 사용자에게는 고정 문구만 나간다.
    """

    name: str

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse: ...
