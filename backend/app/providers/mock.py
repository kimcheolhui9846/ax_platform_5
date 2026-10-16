"""비용 0, 결정적인 Mock 제공자. 개발·테스트의 기본값이다."""
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderError, ProviderOutputError, ProviderResponse, Usage
from app.providers.mock_fill import mock_instance


class MockProvider:
    name = "mock"

    def __init__(
        self,
        fail_stages: set[str] | None = None,
        output_errors: dict[str, int] | None = None,
    ) -> None:
        # 테스트용: fail_stages의 단계는 항상 실패, output_errors는 단계별로 n번 스키마 오류를 낸다.
        self.fail_stages = fail_stages or set()
        self.output_errors = dict(output_errors or {})
        self.calls: list[tuple[str, str]] = []

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: Prompt,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        self.calls.append((task_type, stage))
        if stage in self.fail_stages:
            raise ProviderError(f"[mock] {stage} 단계 호출 실패")
        if self.output_errors.get(stage, 0) > 0:
            self.output_errors[stage] -= 1
            raise ProviderOutputError(f"[mock] {stage} 단계 응답이 스키마를 통과하지 못함")

        parsed = mock_instance(response_model) if response_model else None
        text = parsed.model_dump_json() if parsed else f"[mock] {stage}"
        return ProviderResponse(
            text=text,
            model="mock",
            parsed=parsed,
            usage=Usage(input_tokens=len(prompt.system) + len(prompt.user), output_tokens=len(text)),
        )
