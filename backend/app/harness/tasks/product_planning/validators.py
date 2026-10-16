"""상품기획 전용 검증 규칙(설계서 7.2 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator

MAX_CORE_FEATURES = 5


def check_mvp_not_too_big(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    features = result.content.get("core_features", [])
    if len(features) <= MAX_CORE_FEATURES:
        return []
    return [
        ValidationIssue(
            rule="mvp_too_big",
            message=f"핵심 기능이 {len(features)}개입니다. MVP는 {MAX_CORE_FEATURES}개 이하로 줄여 보세요.",
        )
    ]


VALIDATORS: list[Validator] = [check_mvp_not_too_big]
