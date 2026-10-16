from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.state import Answer, AnswerType, SessionState
from app.harness.base import BaseHarness
from app.providers.mock import MockProvider

SAMPLE_TASK_DIR = Path(__file__).parent / "fixtures" / "sample_task"


class SampleContent(BaseModel):
    summary: str = Field(description="요약")
    actions: list[str] = Field(description="실행 과제")


class SampleHarness(BaseHarness):
    content_model = SampleContent


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def harness(provider) -> SampleHarness:
    return SampleHarness(SAMPLE_TASK_DIR, provider)


@pytest.fixture
def reply():
    """지금 걸려 있는 질문에 답한다."""

    def _reply(
        harness: BaseHarness,
        state: SessionState,
        answer_type: AnswerType,
        value: str | None = None,
        option_ids: tuple[str, ...] = (),
    ) -> None:
        harness.apply_answer(
            state,
            Answer(
                question_id=state.pending_question.question_id,
                answer_type=answer_type,
                value=value,
                option_ids=list(option_ids),
            ),
        )

    return _reply


CLIENT_ID = "test-client-0001"
OTHER_CLIENT_ID = "test-client-0002"


def api_client(app, client_id: str | None = CLIENT_ID) -> TestClient:
    """익명 사용자 ID(X-Client-Id)를 붙여 보내는 테스트 클라이언트. None이면 헤더를 보내지 않는다."""
    headers = {} if client_id is None else {"X-Client-Id": client_id}
    return TestClient(app, headers=headers)
