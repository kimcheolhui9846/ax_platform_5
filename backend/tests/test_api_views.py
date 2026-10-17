import pytest

from app.api.views import build_summary, session_error, to_result_view, to_session_summary, to_task_form, to_task_summary
from app.core.messages import GENERATION_FAILED_MESSAGE
from app.core.state import Assumption, InfoItem, InfoSource, SessionState, SessionStatus
from app.harness.policy import FieldKind, FieldPolicy, TaskPolicy


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
        to_result_view(SessionState(task_type="t"), _fields(), [])


@pytest.mark.parametrize("status", list(SessionStatus))
def test_session_error_is_derived_from_status(status):
    expected = GENERATION_FAILED_MESSAGE if status is SessionStatus.FAILED else None
    assert session_error(status) == expected


def test_task_views_take_only_the_policy():
    policy = TaskPolicy(
        task_type="t", title="제목", description="설명", heading="하고 싶어요", deliverable="기획서", fields=_fields()
    )
    assert to_task_summary(policy).model_dump() == {
        "task_type": "t",
        "title": "제목",
        "description": "설명",
        "heading": "하고 싶어요",
        "deliverable": "기획서",
    }
    form = to_task_form(policy)
    assert [m.question_cap for m in form.modes] == [3, 5, 10]
    assert [f.label for f in form.fields] == ["가", "나", "다"]


def test_session_summary_takes_only_the_task_title():
    summary = to_session_summary(SessionState(task_type="t", raw_input="향초"), "상품기획")
    assert (summary.title, summary.raw_input, summary.latest_version, summary.saved_versions) == ("상품기획", "향초", None, [])
