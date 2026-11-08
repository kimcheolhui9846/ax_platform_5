"""TC-SEC-009: SQL 명령 같은 문자열이 일반 글자로 처리된다(SQLite 저장소로 실제 DB를 거쳐 확인)."""
import pytest

from app.core.store import SqliteSessionStore
from app.main import create_app
from app.providers.image import MockImageProvider
from tests.acceptance.flow import BASE, answer, answer_all, generate, start
from tests.conftest import api_client

PAYLOADS = ["' OR '1'='1", "test'; DROP TABLE x;--", "test'; DROP TABLE sessions;--"]


@pytest.fixture
def sql_client(recorder, tmp_path):
    store = SqliteSessionStore(tmp_path / "sessions.db")
    return api_client(create_app(provider=recorder, store=store, images=MockImageProvider(), debug=False))


@pytest.mark.parametrize("payload", PAYLOADS)
def test_qa_sec_009_sql_like_request_text_is_stored_as_plain_text(sql_client, payload):
    other = start(sql_client, "business_plan")  # 먼저 만든 다른 세션이 지워지거나 섞이지 않는지 본다
    view = start(sql_client, "business_plan", payload)
    assert view["raw_input"] == payload

    again = sql_client.get(f"{BASE}/sessions/{view['session_id']}")
    assert again.status_code == 200 and again.json()["raw_input"] == payload
    listed = sql_client.get(f"{BASE}/sessions")
    assert listed.status_code == 200
    assert {s["session_id"] for s in listed.json()} == {other["session_id"], view["session_id"]}  # 목록 정상, 표가 그대로


@pytest.mark.parametrize("payload", PAYLOADS)
def test_qa_sec_009_sql_like_free_text_answer_is_stored_as_plain_text(sql_client, payload):
    view = start(sql_client, "business_plan")
    field = view["next_question"]["field"]
    after = answer(sql_client, view, payload)
    assert next(i for i in after["summary"] if i["field"] == field)["value"] == payload

    done, _ = answer_all(sql_client, after)
    result = generate(sql_client, done["session_id"])  # 이어지는 흐름(생성)도 정상
    assert result["session_id"] == done["session_id"]
    assert sql_client.get(f"{BASE}/sessions").status_code == 200
