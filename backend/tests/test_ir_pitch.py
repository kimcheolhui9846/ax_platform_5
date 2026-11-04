"""IR 피치덱 과제: 결과 스키마와 과제 전용 검증 규칙."""
import pytest
from pydantic import ValidationError

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.tasks.ir_pitch.output_schema import IrPitchContent
from app.harness.tasks.ir_pitch.validators import (
    VALIDATORS,
    check_ask_present,
    check_core_slides,
    check_unsupported_investor_claims,
)

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
