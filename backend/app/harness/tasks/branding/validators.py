"""브랜딩 전용 검증 규칙(설계서 7.3 금지·주의)."""
from app.harness.validation import Validator, term_rule

DEFINITIVE_NAMING = ("이 이름으로 확정", "바로 사용하세요", "상표 문제 없음")

check_naming_not_definitive = term_rule(
    "naming_not_definitive",
    DEFINITIVE_NAMING,
    "상표·도메인 검토 전에 이름을 확정적으로 권고하는 표현이 있습니다.",
)


VALIDATORS: list[Validator] = [check_naming_not_definitive]
