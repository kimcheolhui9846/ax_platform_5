"""익명 사용자(owner): 세션 경로는 X-Client-Id가 필요하고, 남의 세션은 없는 세션과 같다."""
import pytest

from app.api.owner import parse_owner
from app.core.messages import CLIENT_ID_REQUIRED_MESSAGE, SESSION_NOT_FOUND_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import OTHER_CLIENT_ID, api_client

BASE = "/api/v1/coaching"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3f2b8c1e-9a4d-4c2b-8f1e-2a3b4c5d6e7f", "3f2b8c1e-9a4d-4c2b-8f1e-2a3b4c5d6e7f"),
        ("abcdef0123456789abcdef0123456789", "abcdef0123456789abcdef0123456789"),
        (None, None),
        ("", None),
        ("짧음", None),
        ("short", None),
        ("a" * 65, None),
        ("bad id!!", None),
    ],
)
def test_parse_owner(value, expected):
    assert parse_owner(value) == expected


def test_task_routes_are_open_without_client_id():
    anonymous = api_client(create_app(provider=MockProvider(), debug=True), client_id=None)
    assert anonymous.get(f"{BASE}/tasks").status_code == 200
    assert anonymous.get(f"{BASE}/tasks/product_planning/form").status_code == 200


@pytest.mark.parametrize("client_id", [None, "bad id!!"])
def test_session_routes_need_a_valid_client_id(client_id):
    client = api_client(create_app(provider=MockProvider(), debug=True), client_id=client_id)

    created = client.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"})
    read = client.get(f"{BASE}/sessions/sess_1")
    listed = client.get(f"{BASE}/sessions")

    for response in (created, read, listed):
        assert response.status_code == 422
        assert response.json() == {"detail": CLIENT_ID_REQUIRED_MESSAGE}


def test_other_clients_session_looks_missing_everywhere():
    app = create_app(provider=MockProvider(), debug=True)
    mine, theirs = api_client(app), api_client(app, client_id=OTHER_CLIENT_ID)
    view = mine.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}).json()
    sid, qid = view["session_id"], view["next_question"]["question_id"]

    attempts = [
        ("GET", f"/sessions/{sid}", None),
        ("POST", f"/sessions/{sid}/answers", {"question_id": qid, "answer_type": "skip"}),
        ("PATCH", f"/sessions/{sid}/answers/{qid}", {"answer_type": "free_text", "value": "남의 답"}),
        ("POST", f"/sessions/{sid}/generate", None),
        ("POST", f"/sessions/{sid}/continue", None),
        ("POST", f"/sessions/{sid}/question/original", None),
        ("GET", f"/sessions/{sid}/result", None),
        ("GET", f"/sessions/{sid}/trace", None),
        ("GET", f"/sessions/{sid}/versions/1", None),
        ("POST", f"/sessions/{sid}/versions/1/save", None),
        ("PATCH", f"/sessions/{sid}/result/sections/1", {"text": "남의 문구"}),
        ("PUT", f"/sessions/{sid}/supplements", {"values": {}}),
    ]
    for method, path, body in attempts:
        response = theirs.request(method, f"{BASE}{path}", json=body)
        assert response.status_code == 404, (method, path)
        assert response.json() == {"detail": SESSION_NOT_FOUND_MESSAGE}, (method, path)

    assert len(app.state.locks) == 0  # 남의 요청은 잠금도 만들지 않는다
    after = mine.get(f"{BASE}/sessions/{sid}").json()
    assert after["next_question"]["question_id"] == qid  # 남의 요청이 내 세션을 바꾸지 않았다


def test_trace_is_closed_without_debug_even_without_client_id():
    anonymous = api_client(create_app(provider=MockProvider(), debug=False), client_id=None)
    response = anonymous.get(f"{BASE}/sessions/sess_1/trace")
    assert response.status_code == 404
    assert response.json() == {"detail": "찾을 수 없습니다."}


def test_openapi_declares_the_client_id_header():
    spec = api_client(create_app(provider=MockProvider(), debug=True)).get("/openapi.json").json()
    scheme = spec["components"]["securitySchemes"]["ClientId"]
    assert (scheme["type"], scheme["in"], scheme["name"]) == ("apiKey", "header", "X-Client-Id")
    assert spec["paths"]["/api/v1/coaching/sessions/{session_id}"]["get"]["security"] == [{"ClientId": []}]
    assert "security" not in spec["paths"]["/api/v1/coaching/tasks"]["get"]
