from app.core.results import ValidationIssue, ValidationReport
from app.core.state import CoachingMode, SessionState, SessionStatus
from app.core.store import InMemorySessionStore


def test_new_session_defaults():
    state = SessionState(task_type="product_planning")
    assert state.session_id.startswith("sess_")
    assert state.mode is CoachingMode.STANDARD
    assert state.status is SessionStatus.DRAFTING
    assert state.facts == {}
    assert state.trace == []
    assert state.pending_question is None


def test_store_returns_independent_copies():
    store = InMemorySessionStore()
    state = SessionState(task_type="branding")
    store.save(state)

    loaded = store.get(state.session_id)
    loaded.raw_input = "바뀐 값"

    assert store.get(state.session_id).raw_input == ""


def test_store_missing_session_returns_none():
    assert InMemorySessionStore().get("sess_없음") is None


def test_validation_report_passes_only_without_errors():
    warning = ValidationIssue(rule="r", message="m")
    error = ValidationIssue(rule="r", message="m", severity="error")
    assert ValidationReport(issues=[warning]).passed
    assert not ValidationReport(issues=[warning, error]).passed
