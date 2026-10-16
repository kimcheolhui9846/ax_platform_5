"""마케팅 콘텐츠 전용 검증 규칙(설계서 7.4 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator, term_rule

EXAGGERATIONS = ("100%", "무조건", "완벽한 효과", "최고의 효능")


def check_cta_present(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    if str(result.content.get("cta", "")).strip():
        return []
    return [ValidationIssue(rule="cta_present", message="행동 유도(CTA)가 없습니다.", severity="error")]


check_no_exaggeration = term_rule(
    "no_exaggeration", EXAGGERATIONS, "과장 광고로 보일 수 있는 표현이 있습니다: {terms}"
)


VALIDATORS: list[Validator] = [check_cta_present, check_no_exaggeration]
