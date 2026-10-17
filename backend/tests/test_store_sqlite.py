"""SQLite 저장소만의 성질: 파일에 남아 서버를 다시 켜도 그대로다."""
from app.core.state import AnswerType
from app.core.store import SqliteSessionStore


def test_sessions_survive_a_new_store_on_the_same_file(tmp_path, harness, reply):
    path = tmp_path / "nested" / "sessions.db"  # 없는 폴더도 만든다
    state = harness.start("향초", owner_id="client-aaaa")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    SqliteSessionStore(path).save(state)

    reopened = SqliteSessionStore(path)

    assert reopened.get(state.session_id) == state
    assert [s.session_id for s in reopened.list_by_owner("client-aaaa")] == [state.session_id]
