"""IR 피치덱 전용 검증 규칙(투자 요청 필수, 핵심 슬라이드, 근거 없는 수치 주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator, term_rule

CORE_SLIDES = ("problem", "solution", "ask")
SLIDE_LABELS = {"problem": "문제", "solution": "해결", "ask": "투자 요청"}
UNSUPPORTED_CLAIMS = ("기업가치", "밸류에이션", "시장 규모", "TAM", "예상 매출", "매출 전망")


def check_ask_present(state: SessionState, result: GenerationResult, policy: TaskPolicy) -> list[ValidationIssue]:
    if str(result.content.get("ask", "")).strip():
        return []
    return [ValidationIssue(rule="ask_present", message="투자 요청(금액·용도)이 없습니다.", severity="error")]


def check_core_slides(state: SessionState, result: GenerationResult, policy: TaskPolicy) -> list[ValidationIssue]:
    present = {s.get("slide_type") for s in result.content.get("slides", [])}
    missing = [SLIDE_LABELS[t] for t in CORE_SLIDES if t not in present]
    if not missing:
        return []
    return [ValidationIssue(rule="core_slides", message=f"핵심 슬라이드가 빠졌습니다: {', '.join(missing)}")]


check_unsupported_investor_claims = term_rule(
    "unsupported_investor_claims",
    UNSUPPORTED_CLAIMS,
    "근거 확인이 필요한 표현이 있습니다: {terms}. 출처가 없다면 가정으로 표시하세요.",
)


VALIDATORS: list[Validator] = [check_ask_present, check_core_slides, check_unsupported_investor_claims]
