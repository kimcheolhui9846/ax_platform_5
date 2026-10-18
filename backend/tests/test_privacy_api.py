"""비공개 설정은 답·보완 정보 요청에 실린다. 고지 동의가 있어야 세션을 만든다."""
from app.core.messages import NOTICE_REQUIRED_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


def new_session(client, task="product_planning", text="향초"):
    return client.post(f"{BASE}/tasks/{task}/sessions", json={"raw_input": text, "notice_acknowledged": True}).json()


def test_creating_a_session_needs_the_notice():
    client = api_client(create_app(provider=MockProvider()))
    missing = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초"})
    refused = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초", "notice_acknowledged": False})
    assert missing.status_code == 422
    assert (refused.status_code, refused.json()["detail"]) == (422, NOTICE_REQUIRED_MESSAGE)
    view = new_session(client)
    assert view["private_names"] == ["production_cost", "sale_price"]
    assert {s["name"]: s["private"] for s in view["supplements"]}["sale_price"] is True


def test_answer_can_mark_its_field_private():
    client = api_client(create_app(provider=MockProvider()))
    view = new_session(client)
    q = view["next_question"]
    after = client.post(
        f"{BASE}/sessions/{view['session_id']}/answers",
        json={"question_id": q["question_id"], "answer_type": "free_text", "value": "비밀 답", "private": True},
    ).json()
    assert q["field"] in after["private_names"]
    assert next(s for s in after["summary"] if s["field"] == q["field"])["private"] is True


def test_supplements_can_unmark_a_default_private_item_and_reject_unknown_names():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    saved = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"sale_price": "18,000원"}, "private": {"sale_price": False}}).json()
    assert "sale_price" not in saved["private_names"]
    bad = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"nope": True}})
    assert bad.status_code == 422


def test_changing_only_privacy_makes_the_result_stale_and_reverting_makes_it_current():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    client.post(f"{BASE}/sessions/{sid}/generate")
    stale = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"sale_price": False}}).json()
    assert stale["result_stale"] is True
    back = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"sale_price": True}}).json()
    assert back["result_stale"] is False


def test_result_view_marks_private_rows_from_its_version():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"sale_price": "18,000원"}})
    result = client.post(f"{BASE}/sessions/{sid}/generate").json()
    assert next(s for s in result["supplements"] if s["name"] == "sale_price")["private"] is True
