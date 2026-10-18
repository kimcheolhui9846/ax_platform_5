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


def _all_trace_inputs(client, sid) -> str:
    import json

    return json.dumps([e["input"] for e in client.get(f"{BASE}/sessions/{sid}/trace").json()], ensure_ascii=False)


def test_carrying_a_private_field_keeps_it_private_in_the_next_task():
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    prev = new_session(client, task="branding", text="비밀상품설명XYZ")["session_id"]
    state = app.state.store.get(prev)
    state.private_overrides["product_and_customer"] = True  # 이전 작업에서 사용자가 비공개로 정했다
    app.state.store.save(state)
    client.post(f"{BASE}/sessions/{prev}/generate")

    preview = client.get(f"{BASE}/tasks/marketing_content/context", params={"session_id": prev}).json()
    assert {"field": "product", "label": "홍보 상품", "value": "비밀상품설명XYZ", "private": True} in preview["items"]
    view = client.post(
        f"{BASE}/tasks/marketing_content/sessions",
        json={"raw_input": "홍보 글", "notice_acknowledged": True, "from_session_id": prev},
    ).json()
    assert "product" in view["private_names"]
    client.post(f"{BASE}/sessions/{view['session_id']}/generate")
    assert "비밀상품설명XYZ" not in _all_trace_inputs(client, view["session_id"])


def test_carrying_a_private_supplement_keeps_it_private_in_the_next_task():
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    prev = new_session(client)["session_id"]
    client.put(f"{BASE}/sessions/{prev}/supplements", json={"values": {"target_customer": "비밀고객ABC"}, "private": {"target_customer": True}})
    client.post(f"{BASE}/sessions/{prev}/generate")

    view = client.post(
        f"{BASE}/tasks/business_plan/sessions",
        json={"raw_input": "사업 아이디어", "notice_acknowledged": True, "from_session_id": prev},
    ).json()
    assert "target_customer" in view["private_names"]
    client.post(f"{BASE}/sessions/{view['session_id']}/generate")
    assert "비밀고객ABC" not in _all_trace_inputs(client, view["session_id"])


def test_easier_answer_can_mark_its_field_private():
    client = api_client(create_app(provider=MockProvider()))
    view = new_session(client)
    q = view["next_question"]
    after = client.post(
        f"{BASE}/sessions/{view['session_id']}/answers",
        json={"question_id": q["question_id"], "answer_type": "easier", "private": True},
    ).json()
    assert after["next_question"]["field"] == q["field"]
    assert q["field"] in after["private_names"]


def test_unknown_task_or_foreign_previous_session_is_404_before_the_notice_check():
    from tests.conftest import OTHER_CLIENT_ID

    app = create_app(provider=MockProvider())
    client = api_client(app)
    unknown = client.post(f"{BASE}/tasks/nope/sessions", json={"raw_input": "x", "notice_acknowledged": False})
    assert unknown.status_code == 404
    prev = new_session(client)["session_id"]
    other = api_client(app, client_id=OTHER_CLIENT_ID)
    foreign = other.post(
        f"{BASE}/tasks/branding/sessions", json={"raw_input": "x", "notice_acknowledged": False, "from_session_id": prev}
    )
    assert foreign.status_code == 404


def test_supplements_privacy_accepts_only_supplement_names():
    client = api_client(create_app(provider=MockProvider()))
    view = new_session(client)
    field = view["next_question"]["field"]
    bad = client.put(f"{BASE}/sessions/{view['session_id']}/supplements", json={"values": {}, "private": {field: True}})
    assert bad.status_code == 422


def test_clearing_the_context_also_drops_the_privacy_it_brought():
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    prev = new_session(client, task="branding", text="비밀상품설명XYZ")["session_id"]
    state = app.state.store.get(prev)
    state.private_overrides["product_and_customer"] = True
    app.state.store.save(state)
    client.post(f"{BASE}/sessions/{prev}/generate")
    view = client.post(
        f"{BASE}/tasks/marketing_content/sessions",
        json={"raw_input": "새요청글QRS", "notice_acknowledged": True, "from_session_id": prev},
    ).json()
    sid = view["session_id"]
    assert "product" in view["private_names"]

    cleared = client.delete(f"{BASE}/sessions/{sid}/context").json()
    assert cleared["private_names"] == ["price"]  # 정책 기본값으로 돌아간다
    client.post(f"{BASE}/sessions/{sid}/generate")
    generate = [e for e in client.get(f"{BASE}/sessions/{sid}/trace").json() if e["stage"] == "generate"][-1]
    assert "새요청글QRS" in generate["input"]["user"]
