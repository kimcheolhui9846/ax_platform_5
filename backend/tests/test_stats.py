"""평가 통계: 저장된 세션에서 기획서 14장 지표 중 앱 기록으로 셀 수 있는 것을 과제별로 낸다."""
from datetime import datetime, timezone

import pytest

from app.core.results import GenerationResult, ValidationIssue, ValidationReport, VersionReason
from app.core.state import (
    AnswerType,
    AskedQuestion,
    CarriedContext,
    InfoItem,
    InfoSource,
    Question,
    ResultVersion,
    SessionState,
)
from app.harness.stats import metrics_table, session_metrics

NOW = datetime(2026, 10, 19, tzinfo=timezone.utc)
MUST = {"branding": frozenset({"a", "b"})}


def fact(value="값"):
    return InfoItem(value=value, source=InfoSource.USER_FREE_TEXT)


def version(n, reason, facts=(), saved=False, issues=()):
    return ResultVersion(
        version=n,
        created_at=NOW,
        reason=reason,
        result=GenerationResult(sections=[], full_text="", content={}),
        validation=ValidationReport(issues=[ValidationIssue(rule=r, message=r) for r in issues]),
        facts={name: fact() for name in facts},
        saved=saved,
    )


def asked(answer_type):
    return AskedQuestion(question=Question(question_id="q", field="a", text="질문"), answer_type=answer_type)


def test_session_metrics_counts_per_task():
    done = SessionState(session_id="s1", task_type="branding")
    done.asked_questions = [asked(AnswerType.FREE_TEXT), asked(AnswerType.SKIP), asked(None)]
    done.versions = [
        version(1, VersionReason.FIRST, facts=["a"], issues=["assumptions_marked"]),
        version(2, VersionReason.EDIT, facts=["a"], saved=True),
        version(3, VersionReason.REGENERATE, facts=["a", "b"]),
    ]
    dropped = SessionState(session_id="s2", task_type="branding")
    dropped.asked_questions = [asked(AnswerType.FREE_TEXT)]
    follow = SessionState(session_id="s3", task_type="product_planning")
    follow.context = CarriedContext(session_id="s1", task_type="branding", version=3, title="t", summary="")

    [branding, planning] = session_metrics([done, dropped, follow], MUST)

    assert branding.task == "branding"
    assert (branding.sessions, branding.reached_result) == (2, 1)
    assert branding.dropout_rate == pytest.approx(0.5)
    assert branding.required_fill == pytest.approx(0.5)  # 첫 결과 때 a만 사실
    assert branding.questions_answered == pytest.approx(1.5)  # (2 + 1) / 2, 걸린 질문은 세지 않는다
    assert branding.assumption_marked_rate == pytest.approx(2 / 3)
    assert branding.edits == pytest.approx(1.0)
    assert branding.regenerations == pytest.approx(1.0)
    assert branding.adoption_rate == pytest.approx(1.0)
    assert branding.conversion_rate == pytest.approx(1.0)
    assert planning.sessions == 1 and planning.reached_result == 0
    assert planning.required_fill is None and planning.adoption_rate is None


def test_metrics_table_renders_rates_as_percent():
    [row] = session_metrics([SessionState(task_type="branding")], MUST)
    table = metrics_table([row])
    assert "| branding | 1 | 0 | 100% |" in table
    assert "-" in table
