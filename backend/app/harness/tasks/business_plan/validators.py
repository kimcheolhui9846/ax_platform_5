"""사업계획 전용 검증 규칙(설계서 7.1 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator, find_terms

UNSUPPORTED_CLAIMS = ("시장 규모", "매출 전망", "예상 매출")


def check_unsupported_market_claims(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    hits = find_terms(result.full_text, UNSUPPORTED_CLAIMS)
    if not hits:
        return []
    return [
        ValidationIssue(
            rule="unsupported_market_claims",
            message=f"근거 확인이 필요한 표현이 있습니다: {', '.join(hits)}. 출처가 없다면 가정으로 표시하세요.",
        )
    ]


VALIDATORS: list[Validator] = [check_unsupported_market_claims]
