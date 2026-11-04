"""IR 피치덱 과제: 결과 스키마와 과제 전용 검증 규칙."""
import pytest
from pydantic import ValidationError

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.prompting import context_keys
from app.harness.registry import TASK_TYPES, HarnessRegistry
from app.harness.tasks.ir_pitch.output_schema import IrPitchContent
from app.harness.tasks.ir_pitch.validators import (
    VALIDATORS,
    check_ask_present,
    check_core_slides,
    check_unsupported_investor_claims,
)
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_PART, api_client

BASE = "/api/v1/coaching"
POLICY = TaskPolicy(task_type="ir_pitch", title="IR 피치덱", heading="h", deliverable="d", fields=[])
STATE = SessionState(task_type="ir_pitch")


def slide(slide_type: str) -> dict:
    return {"slide_type": slide_type, "headline": "제목 문장", "script": "발표 원고"}


def content(types=("cover", "problem", "solution", "market", "ask"), ask="시드 3억 원, 제작 설비") -> dict:
    return {
        "one_liner": "한글 디자인 굿즈 브랜드",
        "slides": [slide(t) for t in types],
        "ask": ask,
        "investor_questions": ["재구매율은 얼마인가요?"],
    }


def result(content_value: dict, full_text: str = "본문") -> GenerationResult:
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    return GenerationResult(sections=sections_from_cards([card]), full_text=full_text, content=content_value)


def test_content_requires_five_to_twelve_slides():
    IrPitchContent.model_validate(content())
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("cover", "problem", "ask")))
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("problem",) * 13))


def test_content_rejects_unknown_slide_type():
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("cover", "problem", "solution", "ask", "appendix")))


def test_missing_ask_is_an_error():
    assert check_ask_present(STATE, result(content()), POLICY) == []
    issues = check_ask_present(STATE, result(content(ask="  ")), POLICY)
    assert [(i.rule, i.severity) for i in issues] == [("ask_present", "error")]


def test_missing_core_slides_is_a_warning_naming_them():
    assert check_core_slides(STATE, result(content()), POLICY) == []
    issues = check_core_slides(STATE, result(content(types=("cover", "market", "team", "traction", "financials"))), POLICY)
    assert [(i.rule, i.severity) for i in issues] == [("core_slides", "warning")]
    assert "문제" in issues[0].message and "해결" in issues[0].message and "투자 요청" in issues[0].message


def test_unsupported_investor_claims_are_flagged():
    assert check_unsupported_investor_claims(STATE, result(content(), "기업가치 100억 원, TAM 1조"), POLICY)
    assert not check_unsupported_investor_claims(STATE, result(content(), "인터뷰 20명 진행"), POLICY)


def test_validators_are_registered_in_order():
    assert VALIDATORS == [check_ask_present, check_core_slides, check_unsupported_investor_claims]


@pytest.fixture(scope="module")
def harness():
    return HarnessRegistry(MockProvider()).get("ir_pitch")


def test_ir_pitch_is_registered_last():
    assert TASK_TYPES[-1] == "ir_pitch"


def test_policy_keeps_money_private_and_images_off(harness):
    policy = harness.policy
    assert policy.title == "IR 피치덱"
    assert policy.raw_input_field == "company_idea"
    assert policy.private_fields == ["funding_amount", "current_revenue"]
    assert policy.image_generation is False


def test_carry_over_takes_ideas_and_customers_from_earlier_tasks(harness):
    carry = harness.policy.carry_over
    assert carry["business_idea"] == "company_idea"
    assert carry["product_idea"] == "company_idea"
    assert carry["customer_problem"] == "problem"
    assert carry["target_customer"] == "target_market"
    assert carry["revenue_model"] == "business_model"


def test_mock_session_generates_a_valid_pitch_deck(harness):
    state = harness.start("한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요")
    harness.generate(state)
    content = harness.content_model.model_validate(state.result.content)
    assert 5 <= len(content.slides) <= 12
    assert state.result.sections


def test_api_runs_ir_pitch_from_business_plan_carry():
    client = api_client(create_app(provider=MockProvider()))
    prev = client.post(
        f"{BASE}/tasks/business_plan/sessions", json={"notice_acknowledged": True, "raw_input": "한글 디자인 북백 사업"}
    ).json()["session_id"]
    client.post(f"{BASE}/sessions/{prev}/generate")
    view = client.post(
        f"{BASE}/tasks/ir_pitch/sessions",
        json={"notice_acknowledged": True, "raw_input": "투자 발표 준비", "from_session_id": prev},
    ).json()
    assert view["task_type"] == "ir_pitch"
    company = next(s for s in view["summary"] if s["field"] == "company_idea")
    assert (company["value"], company["source"]) == ("한글 디자인 북백 사업", "previous_task")


def test_standard_mode_asks_the_investment_purpose(harness):
    from app.core.state import Answer, AnswerType

    state = harness.start("한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요")
    asked = []
    for _ in range(30):
        question = state.pending_question
        if question is None:
            break
        asked.append(question.field)
        harness.apply_answer(
            state, Answer(question_id=question.question_id, answer_type=AnswerType.FREE_TEXT, value="답변 내용입니다")
        )
    assert "investment_purpose" in asked


def test_investor_questions_must_not_be_empty():
    bad = content()
    bad["investor_questions"] = []
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(bad)


def test_private_revenue_model_stays_private_when_carried_into_ir_pitch():
    from app.core.state import InfoItem, InfoSource

    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    prev = client.post(
        f"{BASE}/tasks/business_plan/sessions", json={"notice_acknowledged": True, "raw_input": "한글 굿즈 사업"}
    ).json()
    sid = prev["session_id"]
    state = app.state.store.get(sid)
    state.facts["revenue_model"] = InfoItem(value="비밀수익구조XYZ", source=InfoSource.USER_FREE_TEXT)
    app.state.store.save(state)
    client.post(f"{BASE}/sessions/{sid}/generate")

    preview = client.get(f"{BASE}/tasks/ir_pitch/context", params={"session_id": sid}).json()
    item = next(i for i in preview["items"] if i["field"] == "business_model")
    assert (item["value"], item["private"]) == ("비밀수익구조XYZ", True)
    view = client.post(
        f"{BASE}/tasks/ir_pitch/sessions",
        json={"raw_input": "투자 발표", "notice_acknowledged": True, "from_session_id": sid},
    ).json()
    assert "business_model" in view["private_names"]


SLIDE_NAMES = {
    "cover": "표지", "problem": "문제", "solution": "해결", "market": "시장", "business_model": "비즈니스 모델",
    "traction": "성과", "competition": "경쟁", "team": "팀", "financials": "재무 계획", "ask": "투자 요청",
}


def render_generate_system(harness) -> str:
    """test_tasks.py::test_every_stage_template_renders와 같은 방식으로 generate 단계의 system 블록을 얻는다."""
    state = harness.start("테스트 입력")
    values = {
        "state": state,
        "policy": harness.policy,
        "profile": state.profile,
        "field": harness.policy.fields[0] if harness.policy.fields else None,
        "level": 3,
        "previous": [],
        "result_text": "결과",
        "heading": "섹션 제목",
        "text": "섹션 본문",
        "part": SAMPLE_PART,
    }
    return harness.prompts.render("generate", **{key: values[key] for key in context_keys("generate")}).system


def test_generate_prompt_tells_korean_slide_names(harness):
    """실제 모델이 카드에 'cover —'처럼 영어 종류를 쓴 적이 있다(2026-11-04). 화면에는 한국어 이름을 쓰게 한다."""
    system = render_generate_system(harness)
    for english, korean in SLIDE_NAMES.items():
        assert f"{english}={korean}" in system
