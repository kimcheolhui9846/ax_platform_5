"""TC-SEC-011: 오류 응답에 내부 정보(스택 트레이스, 파일 경로, 쿼리, 키)가 없다. 배포와 같은 DEBUG=false로 본다."""
import re

import pytest
from fastapi.testclient import TestClient

from app.core.store import SqliteSessionStore
from app.main import create_app
from app.providers.image import MockImageProvider
from tests.acceptance.flow import BASE, finished, start
from tests.conftest import CLIENT_ID
from tests.qa.conftest import RecordingProvider

SECRET = r"C:\srv\app\secret_module.py SELECT * FROM sessions api_key=sk-test-0000"
LEAK = re.compile(
    r"Traceback|File \"|\.py\b|[A-Za-z]:\\|/app/|/usr/|site-packages|SELECT |INSERT |DROP |sqlite|psycopg|"
    r"api_key|sk-|Exception|Error\(|line \d+",
    re.IGNORECASE,
)


class ExplodingProvider(RecordingProvider):
    """예상하지 못한 예외(내부 정보가 담긴 메시지)를 내는 제공자 → 500 경로."""

    def complete(self, **kwargs):
        raise RuntimeError(SECRET)


def _client(provider, tmp_path) -> TestClient:
    app = create_app(provider=provider, store=SqliteSessionStore(tmp_path / "s.db"), images=MockImageProvider(), debug=False)
    return TestClient(app, headers={"X-Client-Id": CLIENT_ID}, raise_server_exceptions=False)


def _assert_safe(response, status: int) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"detail"}, body  # {"detail": 한국어 문장}만
    assert isinstance(body["detail"], str)
    assert not LEAK.search(response.text), response.text


@pytest.fixture
def safe_client(recorder, tmp_path):
    return _client(recorder, tmp_path)


def test_qa_sec_011_errors_have_only_a_plain_detail(safe_client):
    c = safe_client
    sid = finished(c, "business_plan")
    weird = "%27%22%3Cscript%3E%3B--%00"
    cases = [
        (c.get("/api/v1/coaching/no-such-path"), 404),
        (c.get(f"{BASE}/sessions/{sid}/versions/9999"), 404),  # 잘못된 주소 (saved/9999 에 해당)
        (c.post(f"{BASE}/sessions/{sid}/versions/9999/save"), 404),
        (c.get(f"{BASE}/sessions/sess_{weird}"), 404),  # 특수문자 경로
        (c.get(f"{BASE}/tasks/{weird}/form"), 404),
        (c.get(f"{BASE}/sessions/{sid}/versions/abc"), 422),  # 숫자 자리에 글자
        (c.post(f"{BASE}/tasks/business_plan/sessions", content=b"{not json", headers={"Content-Type": "application/json"}), 422),
        (c.post(f"{BASE}/tasks/business_plan/sessions", json={"raw_input": "'\"<>;--", "notice_acknowledged": "x"}), 422),
        (c.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": "q_x", "answer_type": "bogus"}), 422),
        (c.get(f"{BASE}/sessions", headers={"X-Client-Id": "!!"}), 422),  # 형식이 틀린 사용자 ID
        (c.put(f"{BASE}/sessions/{sid}/result"), 405),
    ]
    for response, status in cases:
        _assert_safe(response, status)


def test_qa_sec_011_unexpected_exception_returns_plain_500(tmp_path):
    c = _client(ExplodingProvider(), tmp_path)
    response = c.post(f"{BASE}/tasks/business_plan/sessions", json={"raw_input": "향초", "notice_acknowledged": True})
    _assert_safe(response, 500)
    assert "secret_module" not in response.text and "sk-test" not in response.text


def test_qa_sec_011_trace_is_closed_when_debug_is_off(safe_client):
    """내부 프롬프트·원문 오류가 담긴 trace는 DEBUG=false면 열리지 않는다."""
    view = start(safe_client, "business_plan")
    response = safe_client.get(f"{BASE}/sessions/{view['session_id']}/trace")
    assert response.status_code == 404
    _assert_safe(response, 404)
