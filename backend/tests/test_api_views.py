import pytest

from app.api.views import build_summary, to_result_view
from app.core.state import Assumption, InfoItem, InfoSource, SessionState
from app.harness.policy import FieldKind, FieldPolicy


def _fields() -> list[FieldPolicy]:
    return [
        FieldPolicy(name="a", label="가", kind=FieldKind.MUST_CONFIRM, question="?"),
        FieldPolicy(name="b", label="나", kind=FieldKind.MUST_CONFIRM, question="?"),
        FieldPolicy(name="c", label="다", kind=FieldKind.MUST_CONFIRM, question="?"),
    ]


def test_build_summary_orders_by_policy_and_marks_assumptions():
    facts = {"c": InfoItem(value="사실", source=InfoSource.USER_FREE_TEXT)}
    assumptions = {"a": Assumption(value="가정", source=InfoSource.AI_ASSUMPTION, confidence=0.5)}

    items = build_summary(_fields(), facts, assumptions)

    assert [(i.field, i.label, i.value, i.is_assumption) for i in items] == [
        ("a", "가", "가정", True),
        ("c", "다", "사실", False),
    ]


def test_build_summary_prefers_fact_over_assumption():
    facts = {"a": InfoItem(value="사실", source=InfoSource.USER_FREE_TEXT)}
    assumptions = {"a": Assumption(value="가정", source=InfoSource.AI_ASSUMPTION)}

    [item] = build_summary(_fields(), facts, assumptions)

    assert (item.value, item.is_assumption) == ("사실", False)


def test_to_result_view_requires_result():
    with pytest.raises(ValueError):
        to_result_view(SessionState(task_type="x"))
