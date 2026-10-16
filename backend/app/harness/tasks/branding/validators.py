"""브랜딩 전용 검증 규칙(설계서 7.3 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator, find_terms

DEFINITIVE_NAMING = ("이 이름으로 확정", "바로 사용하세요", "상표 문제 없음")


def check_naming_not_definitive(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    hits = find_terms(result.full_text, DEFINITIVE_NAMING)
    if not hits:
        return []
    return [
        ValidationIssue(
            rule="naming_not_definitive",
            message="상표·도메인 검토 전에 이름을 확정적으로 권고하는 표현이 있습니다.",
        )
    ]


VALIDATORS: list[Validator] = [check_naming_not_definitive]
