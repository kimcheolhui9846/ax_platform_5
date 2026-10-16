from pathlib import Path

import pytest
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
