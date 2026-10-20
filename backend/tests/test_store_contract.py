"""SessionStore 계약. 새 저장소는 store 픽스처에 넣고 이 테스트를 그대로 통과해야 한다."""
from datetime import datetime, timezone

import pytest

from app.core.postgres import PostgresSessionStore
from app.core.state import InfoItem, InfoSource, SessionState, TraceEntry
from app.core.store import InMemorySessionStore, SqliteSessionStore


@pytest.fixture(params=["memory", "sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemorySessionStore()
    if request.param == "sqlite":
        return SqliteSessionStore(tmp_path / "sessions.db")
    return PostgresSessionStore(request.getfixturevalue("postgres_pool"))


def test_missing_id_returns_none(store):
    assert store.get("sess_없음") is None


def test_get_returns_independent_copy(store):
    state = SessionState(task_type="branding")
    store.save(state)

    loaded = store.get(state.session_id)
    loaded.raw_input = "바뀐 값"
    loaded.facts["x"] = InfoItem(value="v", source=InfoSource.USER_FREE_TEXT)

    again = store.get(state.session_id)
    assert again.raw_input == ""
    assert again.facts == {}


def test_save_stores_a_copy(store):
    state = SessionState(task_type="branding")
    store.save(state)

    state.raw_input = "저장 뒤에 바꾼 값"
    state.facts["x"] = InfoItem(value="v", source=InfoSource.USER_FREE_TEXT)

    stored = store.get(state.session_id)
    assert stored.raw_input == ""
    assert stored.facts == {}


def test_save_bumps_updated_at(store):
    long_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
    state = SessionState(task_type="branding", updated_at=long_ago)

    store.save(state)

    assert store.get(state.session_id).updated_at > long_ago


def test_save_overwrites_same_session(store):
    state = SessionState(task_type="branding")
    store.save(state)
    state.raw_input = "두 번째 저장"
    store.save(state)
    assert store.get(state.session_id).raw_input == "두 번째 저장"


def test_list_by_owner_returns_only_that_owners_sessions_newest_first(store, clock):
    first = SessionState(task_type="branding", owner_id="client-aaaa")
    second = SessionState(task_type="product_planning", owner_id="client-aaaa")
    other = SessionState(task_type="branding", owner_id="client-bbbb")
    for state in (first, second, other):
        store.save(state)
    first.raw_input = "다시 저장"
    store.save(first)

    listed = store.list_by_owner("client-aaaa")

    assert [s.session_id for s in listed] == [first.session_id, second.session_id]
    assert listed[0].raw_input == "다시 저장"
    assert store.list_by_owner("client-cccc") == []


def test_list_by_owner_returns_copies(store):
    state = SessionState(task_type="branding", owner_id="client-aaaa")
    store.save(state)

    store.list_by_owner("client-aaaa")[0].raw_input = "목록에서 바꾼 값"

    assert store.get(state.session_id).raw_input == ""


def test_list_by_owner_leaves_out_the_trace(store):
    """목록은 요약만 쓴다. 단계별 프롬프트가 쌓이는 trace는 무거워 빼고 읽는다(get은 그대로 준다)."""
    state = SessionState(task_type="branding", owner_id="client-aaaa")
    state.trace.append(TraceEntry(stage="diagnose", input={"system": "긴 프롬프트"}))
    store.save(state)

    assert store.list_by_owner("client-aaaa")[0].trace == []
    assert len(store.get(state.session_id).trace) == 1


def test_list_all_returns_every_owners_sessions_newest_first_without_trace(store, clock):
    """평가 통계(scripts/session_stats.py)는 모든 사용자의 세션을 본다. 목록처럼 trace는 빼고 읽는다."""
    first = SessionState(task_type="branding", owner_id="client-aaaa")
    second = SessionState(task_type="product_planning", owner_id="client-bbbb")
    first.trace.append(TraceEntry(stage="diagnose"))
    for state in (first, second):
        store.save(state)

    listed = store.list_all()

    assert [s.session_id for s in listed] == [second.session_id, first.session_id]
    assert all(s.trace == [] for s in listed)


def test_delete_removes_only_that_session(store):
    gone = SessionState(task_type="branding", owner_id="client-aaaa")
    kept = SessionState(task_type="branding", owner_id="client-aaaa")
    store.save(gone)
    store.save(kept)

    store.delete(gone.session_id)

    assert store.get(gone.session_id) is None
    assert [s.session_id for s in store.list_by_owner("client-aaaa")] == [kept.session_id]
    assert [s.session_id for s in store.list_all()] == [kept.session_id]
    assert store.get(kept.session_id) is not None


def test_delete_missing_id_is_a_noop(store):
    store.delete("sess_없음")


def test_postgres_store_recovers_after_server_drops_connections(postgres_pool, _postgres_url):
    """Neon이 쉬면서 연결을 끊어도 다음 호출은 죽은 연결을 버리고 새로 연다. 풀에서 꺼낸 그 연결 하나만 끊는다."""
    import psycopg

    store = PostgresSessionStore(postgres_pool)
    state = SessionState(task_type="branding")
    store.save(state)
    with postgres_pool.connection() as conn:
        pid = conn.info.backend_pid
        with psycopg.connect(_postgres_url, autocommit=True) as killer:
            killer.execute("SELECT pg_terminate_backend(%s)", (pid,))

    assert store.get(state.session_id).session_id == state.session_id


def test_stray_nul_never_breaks_save(store):
    state = SessionState(task_type="branding", raw_input="a\x00b")
    store.save(state)
    assert store.get(state.session_id) is not None


def test_without_nul_keeps_escaped_backslash_text():
    from app.core.postgres import without_nul

    nul, literal = chr(92) + "u0000", chr(92) * 2 + "u0000"
    assert without_nul('"a' + nul + 'b"') == '"a' + chr(92) + 'ufffdb"'
    assert without_nul('"a' + literal + 'b"') == '"a' + literal + 'b"'
