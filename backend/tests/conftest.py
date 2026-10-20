import os

# 테스트는 개발자의 backend/.env(STORE=sqlite)와 상관없이 메모리 저장소를 쓴다. app 설정을 읽기 전에 정한다.
os.environ["STORE"] = "memory"

from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

import app.core.postgres as postgres_module
import app.core.store as store_module
from app.core.state import Answer, AnswerType, SessionState
from app.harness.base import BaseHarness
from app.harness.policy import GenerationPart
from app.providers.mock import MockProvider

SAMPLE_TASK_DIR = Path(__file__).parent / "fixtures" / "sample_task"
# generate_part 템플릿 변수(정책에서 오는 값이라 위조 대상이 아니다)
SAMPLE_PART = GenerationPart(name="part", content=["summary"])


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
    monkeypatch.setattr(postgres_module, "utcnow", tick)


@pytest.fixture(scope="session")
def _postgres_url(tmp_path_factory):
    """Postgres 주소 하나를 테스트 세션 동안 쓴다. TEST_DATABASE_URL(셸 환경 변수만 읽는다)이 우선, 없으면 내장 Postgres(pgserver)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        from app.config import settings

        main_url = os.environ.get("DATABASE_URL") or (settings.database_url.get_secret_value() if settings.database_url else "")
        if url == main_url:  # 테스트는 표를 TRUNCATE한다: 실제 데이터를 지우지 않게 막는다
            pytest.skip("TEST_DATABASE_URL이 DATABASE_URL과 같아 건너뜀(테스트 전용 DB를 쓰세요)")
        yield url
        return
    try:
        import pgserver

        server = pgserver.get_server(tmp_path_factory.mktemp("pgdata"), cleanup_mode="stop")
        uri = server.get_uri()
    except Exception as error:  # 주소가 들어간 메시지는 싣지 않는다
        pytest.skip(f"Postgres를 띄울 수 없어 건너뜀: {type(error).__name__}")
    try:
        yield uri
    finally:
        server.cleanup()


@pytest.fixture(scope="session")
def _postgres_pool_session(_postgres_url):
    from app.core.postgres import make_pool, open_pool

    pool = make_pool(_postgres_url)
    open_pool(pool)
    yield pool
    pool.close()


@pytest.fixture
def postgres_pool(_postgres_pool_session):
    """표를 비운 Postgres 풀."""
    with _postgres_pool_session.connection() as conn:
        conn.execute("TRUNCATE sessions, assets")
    return _postgres_pool_session
