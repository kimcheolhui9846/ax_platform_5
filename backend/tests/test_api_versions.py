"""결과 버전 API: 생성 응답에 버전과 그 기준, 버전 보기·저장."""
import pytest

from app.core.messages import VERSION_NOT_FOUND_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


@pytest.fixture
def client():
    return api_client(create_app(provider=MockProvider(), debug=True))


def started(client) -> str:
    view = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "수제 향초"}).json()
    sid, qid = view["session_id"], view["next_question"]["question_id"]
    client.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": qid, "answer_type": "option", "option_ids": ["o2"]})
    return sid


def test_generate_returns_the_version_and_its_basis(client):
    sid = started(client)

    body = client.post(f"{BASE}/sessions/{sid}/generate").json()

    assert body["version"]["version"] == 1
    assert body["version"]["reason"] == "first"
    assert body["version"]["saved"] is False
    assert {"field": "user", "label": "사용자"}.items() <= next(s for s in body["summary"] if s["field"] == "user").items()
    assert body["unknowns"] == []
    assert client.get(f"{BASE}/sessions/{sid}/result").json()["version"] == body["version"]


def test_view_and_save_a_version(client):
    sid = started(client)
    client.post(f"{BASE}/sessions/{sid}/generate")
    client.post(f"{BASE}/sessions/{sid}/generate")

    old = client.get(f"{BASE}/sessions/{sid}/versions/1")
    assert old.status_code == 200
    assert (old.json()["version"]["version"], old.json()["version"]["reason"], old.json()["latest"]) == (1, "first", False)
    assert client.get(f"{BASE}/sessions/{sid}/versions/2").json()["latest"] is True

    saved = client.post(f"{BASE}/sessions/{sid}/versions/2/save")
    assert saved.status_code == 200
    assert saved.json()["version"]["saved"] is True
    assert client.get(f"{BASE}/sessions/{sid}/result").json()["version"]["saved"] is True
    assert client.get(f"{BASE}/sessions/{sid}/versions/1").json()["version"]["saved"] is False


def test_unknown_version_is_404(client):
    sid = started(client)
    client.post(f"{BASE}/sessions/{sid}/generate")

    for response in (
        client.get(f"{BASE}/sessions/{sid}/versions/9"),
        client.post(f"{BASE}/sessions/{sid}/versions/9/save"),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": VERSION_NOT_FOUND_MESSAGE}
    assert client.get(f"{BASE}/sessions/{sid}/versions/abc").status_code == 422
