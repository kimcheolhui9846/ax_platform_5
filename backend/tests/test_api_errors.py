"""오류 계약: 어떤 실패든 본문은 {"detail": "<한국어 문장>"}이고 내부 사정은 로그에만 남는다."""
import logging

import pytest
from tests.conftest import api_client

from app.core.messages import INTERNAL_ERROR_MESSAGE, INVALID_REQUEST_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/coaching"


@pytest.fixture
def client():
    return api_client(create_app(provider=MockProvider(), debug=True))


def test_unknown_path_is_korean_404(client):
    response = client.get("/없는/경로")
    assert response.status_code == 404
    assert response.json() == {"detail": "찾을 수 없습니다."}


def test_wrong_method_is_korean_405(client):
    response = client.delete(f"{BASE}/tasks")
    assert response.status_code == 405
    assert response.json() == {"detail": "허용되지 않는 요청입니다."}
    assert "GET" in response.headers["allow"]


def test_explicit_korean_detail_is_kept(client):
    response = client.get(f"{BASE}/sessions/sess_없음")
    assert response.status_code == 404
    assert response.json() == {"detail": "세션을 찾을 수 없습니다."}


def test_hidden_trace_looks_like_unknown_path():
    client = api_client(create_app(provider=MockProvider(), debug=False))
    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초"}).json()["session_id"]
    response = client.get(f"{BASE}/sessions/{sid}/trace")
    assert response.status_code == 404
    assert response.json() == {"detail": "찾을 수 없습니다."}


def test_unexpected_exception_is_korean_500_and_logged_once(monkeypatch, caplog):
    """예상하지 못한 예외는 한 번만 로그에 남고 서버로 다시 올라가지 않는다(서버가 또 로그를 남기지 않는다)."""
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)  # 예외가 서버까지 올라가면 여기서 그대로 터진다

    def boom(*args, **kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(app.state.registry.get("product_planning"), "start", boom)
    with caplog.at_level(logging.DEBUG):
        response = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "x"})

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_ERROR_MESSAGE}
    assert "secret" not in response.text
    logged = [r for r in caplog.records if r.exc_info and "secret internal detail" in str(r.exc_info[1])]
    assert len(logged) == 1


def test_request_validation_details_are_logged_not_returned(caplog):
    client = api_client(create_app(provider=MockProvider(), debug=False))
    with caplog.at_level(logging.INFO, logger="app.api.errors"):
        response = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": ""})
    assert response.json() == {"detail": INVALID_REQUEST_MESSAGE}
    assert any("raw_input" in r.getMessage() for r in caplog.records)


def test_openapi_documents_error_body_instead_of_validation_error(client):
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    assert schemas["ErrorBody"]["properties"] == {"detail": {"type": "string", "title": "Detail"}}
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas
    responses = spec["paths"][f"{BASE}/sessions/{{session_id}}/answers"]["post"]["responses"]
    for status in ("404", "500", "502"):
        ref = responses[status]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/ErrorBody"), status


def _statuses(spec: dict, path: str, method: str) -> set[str]:
    return set(spec["paths"][f"{BASE}{path}"][method]["responses"])


def test_each_route_declares_only_errors_it_can_return(client):
    spec = client.get("/openapi.json").json()
    assert _statuses(spec, "/tasks", "get") == {"200", "500"}
    assert _statuses(spec, "/tasks/{task_type}/form", "get") == {"200", "404", "500"}
    assert _statuses(spec, "/sessions/{session_id}", "get") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/sessions/{session_id}/result", "get") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/tasks/{task_type}/sessions", "post") == {"201", "404", "422", "500", "502"}
    assert _statuses(spec, "/sessions/{session_id}/answers", "post") == {"200", "404", "422", "500", "502"}
    assert _statuses(spec, "/sessions/{session_id}/generate", "post") == {"200", "404", "422", "500", "502"}
    assert _statuses(spec, "/sessions/{session_id}/continue", "post") == {"200", "404", "422", "500", "502"}
    assert _statuses(spec, "/sessions/{session_id}/answers/{question_id}", "patch") == {"200", "404", "422", "500", "502"}
    assert _statuses(spec, "/sessions/{session_id}/question/original", "post") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/sessions/{session_id}/trace", "get") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/sessions/{session_id}/versions/{version}", "get") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/sessions/{session_id}/versions/{version}/save", "post") == {"200", "404", "422", "500"}
    assert _statuses(spec, "/sessions", "get") == {"200", "422", "500"}


def test_request_error_details_only_in_debug():
    debug = api_client(create_app(provider=MockProvider(), debug=True))
    body = debug.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": ""}).json()
    assert body["detail"] == INVALID_REQUEST_MESSAGE
    assert any("raw_input" in item["loc"] for item in body["errors"])
    assert set(body["errors"][0]) == {"loc", "msg", "type"}

    prod = api_client(create_app(provider=MockProvider(), debug=False))
    body = prod.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": ""}).json()
    assert body == {"detail": INVALID_REQUEST_MESSAGE}


def test_openapi_documents_debug_only_errors_as_optional(client):
    spec = client.get("/openapi.json").json()
    responses = spec["paths"][f"{BASE}/sessions/{{session_id}}/answers"]["post"]["responses"]
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/RequestErrorBody")
    body = spec["components"]["schemas"]["RequestErrorBody"]
    assert body["required"] == ["detail"]
    assert "DEBUG" in body["properties"]["errors"]["description"]
