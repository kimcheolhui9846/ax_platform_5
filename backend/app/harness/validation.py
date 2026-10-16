"""모든 과제에 공통으로 적용하는 출력 검증 규칙. 과제 전용 규칙은 tasks/<task>/validators.py."""
from collections.abc import Callable, Iterable, Sequence

from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy

Validator = Callable[[SessionState, GenerationResult, TaskPolicy], list[ValidationIssue]]


def check_cards_present(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    if result.cards:
        return []
    return [ValidationIssue(rule="cards_present", message="결과 카드가 하나도 없습니다.", severity="error")]


def check_assumptions_marked(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    """세션에 AI 가정이 남아 있는데 결과에 가정 표시가 없으면 경고한다(설계서 12장)."""
    marked = {a.field for a in result.assumptions}
    missing = [name for name in state.assumptions if name not in marked]
    if not missing:
        return []
    labels = ", ".join(policy.labels.get(name, name) for name in missing)
    return [ValidationIssue(rule="assumptions_marked", message=f"AI 가정이 결과에 표시되지 않았습니다: {labels}")]


COMMON_VALIDATORS: list[Validator] = [check_cards_present, check_assumptions_marked]


def collect_issues(
    validators: Iterable[Validator],
    state: SessionState,
    result: GenerationResult,
    policy: TaskPolicy,
) -> list[ValidationIssue]:
    """[코드·순수] 규칙을 차례로 돌려 문제를 모은다."""
    return [issue for check in validators for issue in check(state, result, policy)]


def find_terms(text: str, terms: Sequence[str]) -> list[str]:
    """[코드·순수] terms 중 text에 들어 있는 것을 terms의 순서대로 돌려준다."""
    return [term for term in terms if term in text]
