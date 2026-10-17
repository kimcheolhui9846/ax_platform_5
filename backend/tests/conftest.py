import os

# 테스트는 개발자의 backend/.env(STORE=sqlite)와 상관없이 메모리 저장소를 쓴다. app 설정을 읽기 전에 정한다.
os.environ["STORE"] = "memory"

from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

import app.core.store as store_module
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


@pytest.fixture
def clock(monkeypatch):
    """저장소가 찍는 저장 시각을 1초씩 늘린다(시계 해상도 때문에 같은 시각이 찍혀 순서가 흔들리지 않게)."""
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]

    def tick() -> datetime:
        now[0] += timedelta(seconds=1)
        return now[0]

    monkeypatch.setattr(store_module, "utcnow", tick)
