"""SessionStore 계약. 새 저장소는 store 픽스처에 넣고 이 테스트를 그대로 통과해야 한다."""
from datetime import datetime, timezone

import pytest

from app.core.state import InfoItem, InfoSource, SessionState
from app.core.store import InMemorySessionStore, SqliteSessionStore


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemorySessionStore()
    return SqliteSessionStore(tmp_path / "sessions.db")


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
