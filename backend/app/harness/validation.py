"""모든 과제에 공통으로 적용하는 출력 검증 규칙. 과제 전용 규칙은 tasks/<task>/validators.py."""
from collections.abc import Callable, Iterable, Sequence

from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy

Validator = Callable[[SessionState, GenerationResult, TaskPolicy], list[ValidationIssue]]


def check_sections_present(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    if result.sections:
        return []
    return [ValidationIssue(rule="sections_present", message="결과 섹션이 하나도 없습니다.", severity="error")]


def check_assumptions_marked(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    """세션에 AI 가정이 남아 있는데 결과에 가정 표시가 없으면 경고한다(설계서 12장).

    BaseHarness.generate가 세션 가정을 코드로 합치므로 기본 흐름에서는 걸리지 않는다. generate를
    오버라이드한 과제를 위한 안전망이다. field에 내부 이름 대신 라벨이 적혀도 표시된 것으로 본다.
    """
    marked = {a.field for a in result.assumptions}
    labels = policy.labels
    missing = [
        name for name in state.assumptions if name not in marked and labels.get(name) not in marked
    ]
    if not missing:
        return []
    names = ", ".join(labels.get(name, name) for name in missing)
    return [ValidationIssue(rule="assumptions_marked", message=f"AI 가정이 결과에 표시되지 않았습니다: {names}")]


COMMON_VALIDATORS: list[Validator] = [check_sections_present, check_assumptions_marked]


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


def term_rule(rule: str, terms: Sequence[str], message_template: str) -> Validator:
    """결과 본문에 terms 중 하나라도 있으면 경고 하나를 내는 검증 규칙을 만든다.

    message_template의 {terms}에는 찾은 표현이 쉼표로 이어져 들어간다(없어도 된다).
    """

    def check(state: SessionState, result: GenerationResult, policy: TaskPolicy) -> list[ValidationIssue]:
        hits = find_terms(result.full_text, terms)
        if not hits:
            return []
        return [ValidationIssue(rule=rule, message=message_template.format(terms=", ".join(hits)))]

    check.__name__ = f"check_{rule}"
    return check
