from app.core.results import ValidationIssue, ValidationReport
from app.core.state import CoachingMode, SessionState, SessionStatus


def test_new_session_defaults():
    state = SessionState(task_type="product_planning")
    assert state.session_id.startswith("sess_")
    assert state.mode is CoachingMode.STANDARD
    assert state.status is SessionStatus.DRAFTING
    assert state.facts == {}
    assert state.trace == []
    assert state.pending_question is None


def test_validation_report_passes_only_without_errors():
    warning = ValidationIssue(rule="r", message="m")
    error = ValidationIssue(rule="r", message="m", severity="error")
    assert ValidationReport(issues=[warning]).passed
    assert not ValidationReport(issues=[warning, error]).passed
