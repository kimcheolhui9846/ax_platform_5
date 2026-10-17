"""이어가기 API: 미리보기, from_session_id로 세션 만들기, 가져온 내용 빼기. 남의·없는 이전 세션은 404."""
from app.core.messages import PREVIOUS_SESSION_NOT_FOUND_MESSAGE, VERSION_NOT_FOUND_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import OTHER_CLIENT_ID, api_client

BASE = "/api/v1/coaching"


def finished_product_session(client) -> str:
    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "한글 파우치"}).json()["session_id"]
    client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"target_customer": "직장인"}})
    client.post(f"{BASE}/sessions/{sid}/generate")
    return sid


def test_preview_and_create_share_the_same_context():
    client = api_client(create_app(provider=MockProvider()))
    prev = finished_product_session(client)

    preview = client.get(f"{BASE}/tasks/branding/context", params={"session_id": prev}).json()
    assert preview["title"] == "상품기획 초안 V1"
    assert preview["version"] == 1
    assert {"field": "product_and_customer", "label": "상품과 고객", "value": "한글 파우치"} in preview["items"]

    view = client.post(
        f"{BASE}/tasks/branding/sessions", json={"raw_input": "브랜드 인상", "from_session_id": prev, "from_version": 1}
    ).json()
    assert view["context"] == preview
    carried = next(s for s in view["summary"] if s["field"] == "product_and_customer")
    # 처음 입력 필드는 새 요청 글이 이긴다
    assert (carried["value"], carried["source"]) == ("브랜드 인상", "user_free_text")


def test_marketing_takes_the_customer_from_a_supplement():
    client = api_client(create_app(provider=MockProvider()))
    prev = finished_product_session(client)
    view = client.post(f"{BASE}/tasks/marketing_content/sessions", json={"raw_input": "홍보 글", "from_session_id": prev}).json()
    item = next(s for s in view["summary"] if s["field"] == "target_customer")
    assert (item["value"], item["source"], item["source_label"]) == ("직장인", "previous_task", "이전 과제")
    assert all(f["field"] != "target_customer" or f["status"] != "upcoming" for f in view["flow"])


def test_unknown_or_foreign_previous_sessions_and_versions_are_404():
    app = create_app(provider=MockProvider())
    client = api_client(app)
    prev = finished_product_session(client)
    other = api_client(app, client_id=OTHER_CLIENT_ID)

    for response in (
        other.get(f"{BASE}/tasks/branding/context", params={"session_id": prev}),
        other.post(f"{BASE}/tasks/branding/sessions", json={"raw_input": "x", "from_session_id": prev}),
        client.post(f"{BASE}/tasks/branding/sessions", json={"raw_input": "x", "from_session_id": "sess_nope"}),
    ):
        assert (response.status_code, response.json()) == (404, {"detail": PREVIOUS_SESSION_NOT_FOUND_MESSAGE})
    missing = client.get(f"{BASE}/tasks/branding/context", params={"session_id": prev, "version": 9})
    assert (missing.status_code, missing.json()) == (404, {"detail": VERSION_NOT_FOUND_MESSAGE})
    no_result = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "y"}).json()["session_id"]
    assert client.get(f"{BASE}/tasks/branding/context", params={"session_id": no_result}).status_code == 404
    assert client.get(f"{BASE}/tasks/nope/context", params={"session_id": prev}).status_code == 404


def test_delete_context_removes_carried_values_and_is_idempotent():
    client = api_client(create_app(provider=MockProvider()))
    prev = finished_product_session(client)
    sid = client.post(f"{BASE}/tasks/marketing_content/sessions", json={"raw_input": "홍보 글", "from_session_id": prev}).json()["session_id"]

    cleared = client.delete(f"{BASE}/sessions/{sid}/context")

    assert cleared.status_code == 200
    body = cleared.json()
    assert body["context"] is None
    assert all(s["source"] != "previous_task" for s in body["summary"])
    assert client.delete(f"{BASE}/sessions/{sid}/context").status_code == 200
    assert api_client(client.app, client_id=OTHER_CLIENT_ID).delete(f"{BASE}/sessions/{sid}/context").status_code == 404


def test_sessions_without_a_previous_task_have_no_context():
    client = api_client(create_app(provider=MockProvider()))
    view = client.post(f"{BASE}/tasks/branding/sessions", json={"raw_input": "x"}).json()
    assert view["context"] is None
