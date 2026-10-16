"""사업계획 전용 검증 규칙(설계서 7.1 금지·주의)."""
from app.harness.validation import Validator, term_rule

UNSUPPORTED_CLAIMS = ("시장 규모", "매출 전망", "예상 매출")

check_unsupported_market_claims = term_rule(
    "unsupported_market_claims",
    UNSUPPORTED_CLAIMS,
    "근거 확인이 필요한 표현이 있습니다: {terms}. 출처가 없다면 가정으로 표시하세요.",
)


VALIDATORS: list[Validator] = [check_unsupported_market_claims]
