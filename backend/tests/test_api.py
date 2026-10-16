import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/coaching"


@pytest.fixture
def client():
    return TestClient(create_app(provider=MockProvider(), debug=True))


def create_session(client, task_type="product_planning", raw_input="수제 향초"):
    response = client.post(f"{BASE}/tasks/{task_type}/sessions", json={"raw_input": raw_input})
    assert response.status_code == 201, response.text
    return response.json()


def test_list_tasks(client):
    response = client.get(f"{BASE}/tasks")
    assert response.status_code == 200
    assert [t["task_type"] for t in response.json()] == [
        "business_plan",
        "product_planning",
        "branding",
        "marketing_content",
    ]


def test_task_form(client):
    form = client.get(f"{BASE}/tasks/product_planning/form").json()
    assert form["title"] == "상품기획"
    assert {m["mode"]: m["question_cap"] for m in form["modes"]} == {
        "quick": 3,
        "standard": 5,
        "precise": 10,
    }
    assert form["fields"][0] == {"name": "product_idea", "label": "상품 아이디어", "kind": "must_confirm"}
    assert "rules" not in form


def test_unknown_task_and_session_404(client):
    assert client.get(f"{BASE}/tasks/nope/form").status_code == 404
    assert client.post(f"{BASE}/tasks/nope/sessions", json={"raw_input": "x"}).status_code == 404
    assert client.get(f"{BASE}/sessions/sess_없음").status_code == 404


def test_create_session_returns_first_question(client):
    view = create_session(client)
    assert view["status"] == "clarifying"
    assert view["next_question"]["field"] == "user"
    assert view["progress"] == {"asked": 0, "cap": 5, "readiness": view["progress"]["readiness"]}
    assert view["summary"][0]["field"] == "product_idea"
    assert view["summary"][0]["source"] == "user_free_text"
    assert view["can_generate"] is True
    assert "trace" not in view


def test_full_flow(client):
    view = create_session(client)
    sid = view["session_id"]

    first = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": first["question_id"], "answer_type": "option", "option_ids": ["o1"]},
    ).json()
    assert view["next_question"]["field"] == "usage_context"
    assert view["progress"]["asked"] == 1

    q = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": q["question_id"], "answer_type": "dont_know"}
    ).json()
    assert view["next_question"]["field"] == "usage_context"
    assert view["next_question"]["level"] == 1

    q = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": q["question_id"], "answer_type": "free_text", "value": "집들이 갈 때"},
    ).json()

    revised = client.patch(
        f"{BASE}/sessions/{sid}/answers/{first['question_id']}",
        json={"answer_type": "free_text", "value": "집들이 가는 30대"},
    )
    assert revised.status_code == 200
    assert any(i["value"] == "집들이 가는 30대" for i in revised.json()["summary"])

    result = client.post(f"{BASE}/sessions/{sid}/generate")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    assert body["result"]["cards"]
    assert body["validation"]["passed"] is True

    assert client.get(f"{BASE}/sessions/{sid}/result").json()["result"] == body["result"]
    trace = client.get(f"{BASE}/sessions/{sid}/trace").json()
    assert [t["stage"] for t in trace][0] == "diagnose"


def test_harness_errors_are_422(client):
    sid = create_session(client)["session_id"]
    response = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": "q_엉뚱", "answer_type": "skip"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "지금 답할 수 있는 질문이 아닙니다."


def test_result_before_generate_is_404(client):
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/result").status_code == 404


def test_generate_failure_is_502_and_session_preserved():
    client = TestClient(create_app(provider=MockProvider(fail_stages={"generate"}), debug=True))
    sid = create_session(client)["session_id"]

    response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 502
    assert "다시 시도" in response.json()["detail"]

    view = client.get(f"{BASE}/sessions/{sid}").json()
    assert view["status"] == "failed"
    assert view["error"] == "결과를 만드는 중 문제가 생겼습니다. 잠시 뒤 다시 시도해 주세요."
    assert "[mock]" not in view["error"]
    assert view["summary"][0]["value"] == "수제 향초"


def test_trace_hidden_without_debug():
    client = TestClient(create_app(provider=MockProvider(), debug=False))
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/trace").status_code == 404


CONTRACT_SCHEMAS = (
    "TaskSummary", "TaskForm", "ModeInfo", "FieldSummary", "CreateSessionRequest",
    "AnswerRequest", "ReviseAnswerRequest", "Progress", "SummaryItem", "SessionView",
    "ResultView", "Question", "QuestionOption", "GenerationResult", "ResultCard",
    "ResultAssumption", "ValidationReport", "ValidationIssue", "TraceEntry",
)  # fmt: skip


def test_openapi_has_contract_schemas(client):
    spec = client.get("/openapi.json").json()
    assert f"{BASE}/sessions/{{session_id}}/answers/{{question_id}}" in spec["paths"]
    schemas = spec["components"]["schemas"]
    for name in CONTRACT_SCHEMAS:
        assert name in schemas, name
    assert not [n for n in schemas if n.endswith(("-Input", "-Output"))]
    report = schemas["ValidationReport"]
    assert "passed" in report["properties"]
    assert "passed" in report["required"]


def test_openapi_marks_defaulted_response_fields_required(client):
    """응답 필드는 항상 채워져 나가므로 프론트 타입에서 선택 필드가 되면 안 된다."""
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"question_id", "options"} <= set(schemas["Question"]["required"])
    assert "assumptions" in schemas["GenerationResult"]["required"]
    assert "issues" in schemas["ValidationReport"]["required"]
    # 요청 모델의 기본값 필드는 그대로 선택이다.
    assert "value" not in schemas["AnswerRequest"].get("required", [])
    assert "option_ids" not in schemas["AnswerRequest"].get("required", [])


def test_request_format_errors_are_korean_422(client):
    empty = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": ""})
    assert empty.status_code == 422
    assert empty.json() == {"detail": "요청 형식이 올바르지 않습니다."}

    sid = create_session(client)["session_id"]
    qid = client.get(f"{BASE}/sessions/{sid}").json()["next_question"]["question_id"]
    skip = client.patch(f"{BASE}/sessions/{sid}/answers/{qid}", json={"answer_type": "skip"})
    assert skip.status_code == 422
    assert isinstance(skip.json()["detail"], str)


def test_answer_provider_failure_is_502_and_session_unchanged_with_trace():
    client = TestClient(create_app(provider=MockProvider(fail_stages={"easier_question"}), debug=True))
    sid = create_session(client)["session_id"]
    view = client.get(f"{BASE}/sessions/{sid}").json()
    for _ in range(6):
        before = view
        response = client.post(
            f"{BASE}/sessions/{sid}/answers",
            json={"question_id": view["next_question"]["question_id"], "answer_type": "dont_know"},
        )
        if response.status_code == 502:
            break
        view = response.json()
    else:
        pytest.fail("사다리에서 LLM 호출이 필요해지지 않았다")

    assert response.json()["detail"] == "AI 호출에 실패했습니다. 다시 시도해 주세요."
    after = client.get(f"{BASE}/sessions/{sid}").json()
    assert after["next_question"]["question_id"] == before["next_question"]["question_id"]
    trace = client.get(f"{BASE}/sessions/{sid}/trace").json()
    assert trace[-1]["stage"] == "easier_question"
    assert "error" in trace[-1]["output"]


def test_provider_error_is_502_with_fixed_message(client, monkeypatch):
    from app.providers.base import ProviderError

    def boom(*args, **kwargs):
        raise ProviderError("sk-secret 원문 오류")

    monkeypatch.setattr(client.app.state.registry.get("product_planning"), "start", boom)
    response = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "x"})
    assert response.status_code == 502
    assert response.json()["detail"] == "AI 호출에 실패했습니다. 다시 시도해 주세요."
