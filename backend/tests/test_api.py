import pytest
from fastapi.testclient import TestClient

from app.core.messages import (
    GENERATION_FAILED_MESSAGE,
    INVALID_REQUEST_MESSAGE,
    PROVIDER_FAILED_MESSAGE,
)
from app.harness.stage_models import Diagnosis, ExtractedField
from app.main import create_app
from app.providers.base import ProviderResponse
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
    product = next(t for t in response.json() if t["task_type"] == "product_planning")
    assert product["heading"] == "만들고 싶은 상품을 구체화하고 싶어요"
    assert product["deliverable"] == "상품 콘셉트 · 첫 제작 기획서"


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
    assert view["summary"][0]["source_label"] == "직접 입력"
    assert view["can_generate"] is True
    assert "trace" not in view


def test_session_view_has_request_and_flow(client):
    view = create_session(client, raw_input="수제 향초")

    assert view["raw_input"] == "수제 향초"
    first, *rest = view["flow"]
    assert (first["field"], first["label"], first["status"]) == ("user", "사용자", "current")
    assert first["question"]["question_id"] == view["next_question"]["question_id"]
    assert len(rest) == 4  # 스탠다드 상한 5 = 지금 질문 1 + 예정 4
    assert all(i["status"] == "upcoming" and i["question"] is None and i["answer"] is None for i in rest)


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
        f"{BASE}/sessions/{sid}/answers", json={"question_id": q["question_id"], "answer_type": "easier"}
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


def test_original_question_endpoint(client):
    view = create_session(client)
    sid = view["session_id"]
    first = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": first["question_id"], "answer_type": "easier"}
    ).json()
    assert view["next_question"]["level"] == 1

    back = client.post(f"{BASE}/sessions/{sid}/question/original")
    assert back.status_code == 200
    question = back.json()["next_question"]
    assert (question["field"], question["level"]) == (first["field"], 0)

    again = client.post(f"{BASE}/sessions/{sid}/question/original")
    assert again.status_code == 422
    assert again.json() == {"detail": "기본 질문으로 돌아갈 사다리 질문이 없습니다."}
    assert client.post(f"{BASE}/sessions/sess_없음/question/original").status_code == 404


def test_harness_errors_are_422(client):
    sid = create_session(client)["session_id"]
    response = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": "q_엉뚱", "answer_type": "skip"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "지금 답할 수 있는 질문이 아닙니다."


class UserDiagnosisProvider(MockProvider):
    """처음 입력에서 product_planning의 user 필드를 뽑아 AI 가정을 만든다."""

    def complete(self, *, task_type, stage, prompt, response_model=None):
        if stage == "diagnose":
            parsed = Diagnosis(extracted=[ExtractedField(field="user", value="30대 직장인")])
            return ProviderResponse(text="{}", model="stub", parsed=parsed)
        return super().complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)


def test_labels_reach_assumptions_and_unknowns():
    client = TestClient(create_app(provider=UserDiagnosisProvider(), debug=True))
    view = create_session(client)
    sid = view["session_id"]
    q = view["next_question"]
    assert q["field"] == "user"

    result = client.post(f"{BASE}/sessions/{sid}/generate").json()
    user = next(a for a in result["result"]["assumptions"] if a["field"] == "user")
    assert user == {
        "field": "user",
        "label": "사용자",
        "value": "30대 직장인",
        "reason": "처음 입력에서 추출",
        "requires_confirmation": True,
    }

    view = create_session(client)
    sid = view["session_id"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": view["next_question"]["question_id"], "answer_type": "skip"},
    ).json()
    assert view["unknowns"] == [{"field": "user", "label": "사용자"}]


def test_result_before_generate_is_404(client):
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/result").status_code == 404


def test_generate_failure_is_502_and_session_preserved():
    client = TestClient(create_app(provider=MockProvider(fail_stages={"generate"}), debug=True))
    sid = create_session(client)["session_id"]

    response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 502
    assert response.json() == {"detail": GENERATION_FAILED_MESSAGE}

    view = client.get(f"{BASE}/sessions/{sid}").json()
    assert view["status"] == "failed"
    assert view["error"] == GENERATION_FAILED_MESSAGE
    assert view["summary"][0]["value"] == "수제 향초"


def test_answering_kept_question_after_failed_generate_clears_error():
    """error는 저장값이 아니라 상태에서 나온다. FAILED를 벗어나면 함께 사라진다."""
    client = TestClient(create_app(provider=MockProvider(fail_stages={"generate"}), debug=True))
    view = create_session(client)
    sid = view["session_id"]
    assert client.post(f"{BASE}/sessions/{sid}/generate").status_code == 502

    response = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": view["next_question"]["question_id"], "answer_type": "option", "option_ids": ["o1"]},
    )
    assert response.status_code == 200
    after = response.json()
    assert after["status"] == "clarifying"
    assert after["error"] is None


def test_trace_hidden_without_debug():
    client = TestClient(create_app(provider=MockProvider(), debug=False))
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/trace").status_code == 404


CONTRACT_SCHEMAS = (
    "TaskSummary", "TaskForm", "ModeInfo", "FieldSummary", "CreateSessionRequest",
    "AnswerRequest", "ReviseAnswerRequest", "Progress", "SummaryItem", "SessionView",
    "ResultView", "Question", "QuestionOption", "LabeledResult", "ResultCard",
    "LabeledAssumption", "UnknownItem", "ValidationReport", "ValidationIssue", "TraceEntry",
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
    assert "assumptions" in schemas["LabeledResult"]["required"]
    assert {"label", "reason"} <= set(schemas["LabeledAssumption"]["required"])
    assert "issues" in schemas["ValidationReport"]["required"]
    # 요청 모델의 기본값 필드는 그대로 선택이다.
    assert "value" not in schemas["AnswerRequest"].get("required", [])
    assert "option_ids" not in schemas["AnswerRequest"].get("required", [])


def test_request_format_errors_are_korean_422(client):
    empty = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": ""})
    assert empty.status_code == 422
    assert empty.json()["detail"] == INVALID_REQUEST_MESSAGE

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
            json={"question_id": view["next_question"]["question_id"], "answer_type": "easier"},
        )
        if response.status_code == 502:
            break
        view = response.json()
    else:
        pytest.fail("사다리에서 LLM 호출이 필요해지지 않았다")

    assert response.json()["detail"] == PROVIDER_FAILED_MESSAGE
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
    assert response.json()["detail"] == PROVIDER_FAILED_MESSAGE


def test_failed_regenerate_serves_previous_result_unchanged():
    provider = MockProvider()
    client = TestClient(create_app(provider=provider, debug=True))
    sid = create_session(client)["session_id"]
    first = client.post(f"{BASE}/sessions/{sid}/generate").json()
    assert first["stale"] is False

    provider.fail_stages.add("generate")
    assert client.post(f"{BASE}/sessions/{sid}/generate").status_code == 502

    kept = client.get(f"{BASE}/sessions/{sid}/result").json()
    assert kept["result"] == first["result"]
    assert kept["stale"] is False
    view = client.get(f"{BASE}/sessions/{sid}").json()
    assert (view["status"], view["error"], view["result_stale"]) == ("failed", GENERATION_FAILED_MESSAGE, False)


def test_harness_error_in_generate_is_422(client, monkeypatch):
    from app.harness.errors import HarnessError

    harness = client.app.state.registry.get("product_planning")

    def rule_problem(state):
        raise HarnessError("결과를 만들 수 없는 입력입니다.")

    sid = create_session(client)["session_id"]
    monkeypatch.setattr(harness, "generate", rule_problem)
    response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 422
    assert response.json() == {"detail": "결과를 만들 수 없는 입력입니다."}


def test_continue_after_early_result_returns_next_question(client):
    view = create_session(client)
    sid = view["session_id"]
    assert view["has_result"] is False
    result = client.post(f"{BASE}/sessions/{sid}/generate").json()

    view = client.post(f"{BASE}/sessions/{sid}/continue").json()
    assert view["status"] == "clarifying"
    assert view["next_question"]["field"] == "user"
    assert (view["has_result"], view["result_stale"]) == (True, False)
    assert client.get(f"{BASE}/sessions/{sid}/result").json()["result"] == result["result"]

    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": view["next_question"]["question_id"], "answer_type": "option", "option_ids": ["o1"]},
    ).json()
    assert view["result_stale"] is True


def test_continue_when_nothing_is_left_keeps_session(client):
    sid = create_session(client)["session_id"]
    for _ in range(10):
        view = client.get(f"{BASE}/sessions/{sid}").json()
        if view["next_question"] is None:
            break
        client.post(
            f"{BASE}/sessions/{sid}/answers",
            json={"question_id": view["next_question"]["question_id"], "answer_type": "free_text", "value": "답"},
        )
    client.post(f"{BASE}/sessions/{sid}/generate")
    before = client.get(f"{BASE}/sessions/{sid}").json()
    assert before["status"] == "completed"

    after = client.post(f"{BASE}/sessions/{sid}/continue")
    assert after.status_code == 200
    assert after.json() == before


def test_continue_unknown_session_is_404(client):
    assert client.post(f"{BASE}/sessions/sess_없음/continue").status_code == 404


def _failed_session_with_pending_question():
    provider = MockProvider()
    client = TestClient(create_app(provider=provider, debug=True))
    view = create_session(client)
    sid = view["session_id"]
    first_qid = view["next_question"]["question_id"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": first_qid, "answer_type": "option", "option_ids": ["o1"]},
    ).json()
    assert view["next_question"] is not None
    provider.fail_stages.add("generate")
    assert client.post(f"{BASE}/sessions/{sid}/generate").status_code == 502
    provider.fail_stages.clear()
    assert client.get(f"{BASE}/sessions/{sid}").json()["status"] == "failed"
    return client, sid, first_qid, view["next_question"]["question_id"]


def test_revise_after_failed_generate_clears_failed_and_error():
    client, sid, first_qid, pending_qid = _failed_session_with_pending_question()
    view = client.patch(
        f"{BASE}/sessions/{sid}/answers/{first_qid}", json={"answer_type": "free_text", "value": "부모"}
    ).json()
    assert (view["status"], view["error"]) == ("clarifying", None)
    assert view["next_question"]["question_id"] == pending_qid


def test_continue_after_failed_generate_with_pending_question_is_clarifying():
    client, sid, _, pending_qid = _failed_session_with_pending_question()
    view = client.post(f"{BASE}/sessions/{sid}/continue").json()
    assert (view["status"], view["error"]) == ("clarifying", None)
    assert view["next_question"]["question_id"] == pending_qid


def test_harness_error_in_generate_keeps_llm_trace(client, monkeypatch):
    """규칙 문제(422)로 끝나도 이미 성공한 생성 호출의 기록은 남는다. 세션은 그 밖에 그대로다."""
    from app.harness.errors import HarnessError

    def rule_problem(state, result, policy):
        raise HarnessError("결과를 만들 수 없는 입력입니다.")

    view = create_session(client)
    sid = view["session_id"]
    monkeypatch.setattr(client.app.state.registry.get("product_planning"), "validators", [rule_problem])

    response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 422

    trace = client.get(f"{BASE}/sessions/{sid}/trace").json()
    assert trace[-1]["stage"] == "generate"
    assert "error" not in trace[-1]["output"]
    after = client.get(f"{BASE}/sessions/{sid}").json()
    assert (after["status"], after["next_question"]) == (view["status"], view["next_question"])
    assert after["has_result"] is False
