"""평가 통계: 저장된 세션에서 기획서 14장 지표 중 앱 기록으로 셀 수 있는 것을 과제별로 낸다(순수 함수).

사용성 테스트(Mock으로도 질문 흐름은 그대로다)를 한 뒤 scripts/session_stats.py로 본다. 사실 보존율·출력 품질처럼
사람이 결과를 읽어야 하는 지표와 내려받기처럼 서버에 남지 않는 행동은 여기서 세지 않는다(docs/EVALUATION.md).
"""
from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from app.core.results import VersionReason
from app.core.state import SessionState


class TaskMetrics(BaseModel):
    task: str
    sessions: int
    reached_result: int  # 결과를 한 번이라도 만든 세션
    dropout_rate: float  # 결과 없이 끝난 비율(이탈률의 근사: 아직 진행 중인 세션도 이탈로 센다)
    required_fill: float | None  # 첫 결과 때 반드시 확인(must_confirm) 필드 중 사실로 정해진 비율(필수정보 충족률)
    questions_answered: float  # 세션당 답한 질문 수(질문 효율의 분모, '아직 모르겠어요' 포함)
    assumption_marked_rate: float | None  # 가정 표시 경고(assumptions_marked)가 없는 버전 비율(가정 표시율)
    edits: float | None  # 결과가 있는 세션당 문구 수정 버전 수(수정 횟수)
    regenerations: float | None  # 결과가 있는 세션당 다시 만든 버전 수(답·보완 정보 반영)
    adoption_rate: float | None  # 결과가 있는 세션 중 버전을 저장한 비율(결과 채택률, 내려받기는 세지 않는다)
    conversion_rate: float | None  # 결과가 있는 세션 중 다음 과제로 이어 간 비율(실행 전환율의 근사)


def _ratio(part: float, whole: int) -> float | None:
    return part / whole if whole else None


def _task_metrics(task: str, states: Sequence[SessionState], must: frozenset[str], continued: set[str]) -> TaskMetrics:
    done = [s for s in states if s.versions]
    versions = [v for s in done for v in s.versions]
    fills = [len(must & set(s.versions[0].facts)) / len(must) for s in done] if must else []
    marked = [v for v in versions if v.validation is not None]
    return TaskMetrics(
        task=task,
        sessions=len(states),
        reached_result=len(done),
        dropout_rate=1 - len(done) / len(states),
        required_fill=_ratio(sum(fills), len(fills)),
        questions_answered=sum(sum(1 for q in s.asked_questions if q.answer_type is not None) for s in states) / len(states),
        assumption_marked_rate=_ratio(
            sum(1 for v in marked if not any(i.rule == "assumptions_marked" for i in v.validation.issues)), len(marked)
        ),
        edits=_ratio(sum(1 for v in versions if v.reason is VersionReason.EDIT), len(done)),
        regenerations=_ratio(
            sum(1 for v in versions if v.reason in (VersionReason.REGENERATE, VersionReason.SUPPLEMENT)), len(done)
        ),
        adoption_rate=_ratio(sum(1 for s in done if any(v.saved for v in s.versions)), len(done)),
        conversion_rate=_ratio(sum(1 for s in done if s.session_id in continued), len(done)),
    )


def session_metrics(states: Sequence[SessionState], must_confirm: Mapping[str, frozenset[str]]) -> list[TaskMetrics]:
    """[순수] 과제별 지표(세션이 있는 과제만, 처음 나온 순서). must_confirm은 과제 → 반드시 확인 필드 이름."""
    continued = {s.context.session_id for s in states if s.context is not None}
    by_task: dict[str, list[SessionState]] = {}
    for state in states:
        by_task.setdefault(state.task_type, []).append(state)
    return [
        _task_metrics(task, group, must_confirm.get(task, frozenset()), continued) for task, group in by_task.items()
    ]


def _fmt(value: float | None, percent: bool = True) -> str:
    if value is None:
        return "-"
    return f"{value:.0%}" if percent else f"{value:.1f}"


METRICS_HEADER = (
    "| 과제 | 세션 | 결과 도달 | 이탈률 | 필수정보 충족률 | 답한 질문(세션당) | 가정 표시율 | 수정(세션당) "
    "| 다시 만들기(세션당) | 결과 채택률 | 다음 과제 전환율 |"
)


def metrics_table(rows: Sequence[TaskMetrics]) -> str:
    """[순수] 과제별 지표 표(마크다운)."""
    lines = [METRICS_HEADER, "|" + "---|" * (METRICS_HEADER.count("|") - 1)]
    for r in rows:
        lines.append(
            f"| {r.task} | {r.sessions} | {r.reached_result} | {_fmt(r.dropout_rate)} | {_fmt(r.required_fill)} | "
            f"{_fmt(r.questions_answered, percent=False)} | {_fmt(r.assumption_marked_rate)} | "
            f"{_fmt(r.edits, percent=False)} | {_fmt(r.regenerations, percent=False)} | "
            f"{_fmt(r.adoption_rate)} | {_fmt(r.conversion_rate)} |"
        )
    return "\n".join(lines)
