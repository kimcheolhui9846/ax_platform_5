"""QA TC 검증 공통: 실제 AI를 부르지 않고, AI로 나가는 프롬프트를 모두 기록하는 Mock 제공자."""
import pytest

from app.main import create_app
from app.providers.base import Prompt, ProviderResponse
from app.providers.image import MockImageProvider
from app.providers.mock import MockProvider
from tests.conftest import api_client


class RecordingProvider(MockProvider):
    """MockProvider와 같은 응답을 내고, 받은 (단계, 프롬프트)를 순서대로 남긴다."""

    def __init__(self) -> None:
        super().__init__()
        self.prompts: list[tuple[str, Prompt]] = []

    def complete(self, *, task_type, stage, prompt, response_model=None) -> ProviderResponse:
        self.prompts.append((stage, prompt))
        return super().complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)

    def stages(self) -> list[str]:
        return [stage for stage, _ in self.prompts]

    def outbound_text(self, stage: str | None = None) -> str:
        """기록된 프롬프트(system + user)를 모두 이어 붙인 글. stage를 주면 그 단계만."""
        return "\n".join(p.system + "\n" + p.user for s, p in self.prompts if stage is None or s == stage)


@pytest.fixture
def recorder() -> RecordingProvider:
    return RecordingProvider()


@pytest.fixture
def client(recorder):
    """기록용 Mock 제공자와 Mock 이미지 제공자로 만든 앱(실제 외부 호출 없음)."""
    return api_client(create_app(provider=recorder, images=MockImageProvider()))
