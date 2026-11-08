"""TC-SEC-013: 정해진 방식이 아닌 요청(조회 API에 PUT·DELETE 등)은 405로 안전하게 거절된다."""
import pytest

from app.core.messages import HTTP_STATUS_MESSAGES
from tests.acceptance.flow import BASE, finished

# (경로 템플릿, 허용되지 않는 방식). {sid}는 결과까지 만든 세션 id로 바꾼다.
CASES = [
    ("/tasks", "PUT"),
    ("/tasks", "DELETE"),
    ("/tasks/business_plan/form", "PUT"),
    ("/tasks/business_plan/form", "DELETE"),
    ("/sessions", "PUT"),
    ("/sessions", "DELETE"),
    ("/sessions/{sid}", "PUT"),
    ("/sessions/{sid}/result", "PUT"),
    ("/sessions/{sid}/result", "DELETE"),
    ("/sessions/{sid}/versions/1", "PUT"),
    ("/sessions/{sid}/versions/1", "DELETE"),
    ("/sessions/{sid}/evidence", "PUT"),
    ("/sessions/{sid}/evidence", "DELETE"),
    ("/sessions/{sid}/answers", "GET"),
    ("/sessions/{sid}/generate", "DELETE"),
]


@pytest.mark.parametrize(("path", "method"), CASES)
def test_qa_sec_013_wrong_method_is_rejected_with_405(client, recorder, path, method):
    sid = finished(client, "business_plan")
    before = client.get(f"{BASE}/sessions/{sid}").json()
    calls = len(recorder.prompts)

    response = client.request(method, BASE + path.format(sid=sid), json={})

    assert response.status_code == 405
    assert response.json() == {"detail": HTTP_STATUS_MESSAGES[405]}  # 내부 사정 없이 정해진 한국어 문구만
    assert "allow" in {k.lower() for k in response.headers}  # 허용 방식 안내
    assert len(recorder.prompts) == calls  # AI 호출 없음
    assert client.get(f"{BASE}/sessions/{sid}").json() == before  # 세션이 바뀌지 않음
