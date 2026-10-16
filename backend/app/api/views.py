"""내부 상태 → API 응답 변환. 프론트가 바로 그릴 수 있는 값만 담는다. 모두 순수 함수다."""
from collections.abc import Mapping, Sequence

from app.core.messages import GENERATION_FAILED_MESSAGE
from app.core.results import GenerationResult, ResultAssumption
from app.core.state import Assumption, CoachingMode, InfoItem, SessionState, SessionStatus
from app.harness.base import BaseHarness
from app.harness.policy import FieldPolicy
from app.schemas.coaching import (
    FieldSummary,
    LabeledAssumption,
    LabeledResult,
    ModeInfo,
    Progress,
    ResultView,
    SessionView,
    SummaryItem,
    TaskForm,
    TaskSummary,
    UnknownItem,
)


def to_task_summary(harness: BaseHarness) -> TaskSummary:
    policy = harness.policy
    return TaskSummary(task_type=policy.task_type, title=policy.title, description=policy.description)


def to_task_form(harness: BaseHarness) -> TaskForm:
    policy = harness.policy
    return TaskForm(
        task_type=policy.task_type,
        title=policy.title,
        description=policy.description,
        input_placeholder=policy.input_placeholder,
        input_examples=policy.input_examples,
        modes=[ModeInfo(mode=m, question_cap=policy.question_caps[m]) for m in CoachingMode],
        fields=[FieldSummary(name=f.name, label=f.label, kind=f.kind) for f in policy.fields],
    )


def build_summary(
    fields: Sequence[FieldPolicy],
    facts: Mapping[str, InfoItem],
    assumptions: Mapping[str, Assumption],
) -> list[SummaryItem]:
    """[순수] policy 순서대로 사실(없으면 AI 가정)을 요약 항목으로 만든다."""
    summary: list[SummaryItem] = []
    for f in fields:
        item = facts.get(f.name) or assumptions.get(f.name)
        if item is None:
            continue
        summary.append(
            SummaryItem(
                field=f.name,
                label=f.label,
                value=item.value,
                source=item.source,
                confidence=item.confidence,
                is_assumption=f.name not in facts,
            )
        )
    return summary


def label_unknowns(unknowns: Sequence[str], labels: Mapping[str, str]) -> list[UnknownItem]:
    """[순수] 아직 모르는 필드에 화면용 라벨을 붙인다."""
    return [UnknownItem(field=name, label=labels.get(name, name)) for name in unknowns]


def label_assumptions(
    assumptions: Sequence[ResultAssumption], labels: Mapping[str, str]
) -> list[LabeledAssumption]:
    """[순수] 결과의 가정에 화면용 라벨을 붙인다. policy에 없는 필드는 이름을 그대로 쓴다."""
    return [
        LabeledAssumption(label=labels.get(a.field, a.field), **a.model_dump()) for a in assumptions
    ]


def label_result(result: GenerationResult, labels: Mapping[str, str]) -> LabeledResult:
    """[순수] 저장된 결과를 화면용(라벨 포함) 결과로 바꾼다."""
    return LabeledResult(
        cards=result.cards,
        assumptions=label_assumptions(result.assumptions, labels),
        full_text=result.full_text,
        content=result.content,
        generated_at=result.generated_at,
    )


def session_error(status: SessionStatus) -> str | None:
    """[순수] 사용자에게 보일 오류 문구. 저장하지 않고 상태에서 만든다(FAILED는 생성 실패뿐이다)."""
    return GENERATION_FAILED_MESSAGE if status is SessionStatus.FAILED else None


def to_session_view(state: SessionState, harness: BaseHarness) -> SessionView:
    """can_generate는 비동기 생성을 도입할 때를 위해 남겨 둔 값이다(지금 생성은 동기라 항상 true)."""
    return SessionView(
        session_id=state.session_id,
        task_type=state.task_type,
        mode=state.mode,
        status=state.status,
        next_question=state.pending_question,
        progress=Progress(
            asked=harness.asked_count(state),
            cap=harness.question_cap(state),
            readiness=state.readiness,
        ),
        summary=build_summary(harness.policy.fields, state.facts, state.assumptions),
        unknowns=label_unknowns(state.unknowns, harness.policy.labels),
        can_generate=state.status is not SessionStatus.GENERATING,
        result_stale=state.result_stale,
        error=session_error(state.status),
    )


def to_result_view(state: SessionState, labels: Mapping[str, str]) -> ResultView:
    if state.result is None:
        raise ValueError("생성된 결과가 없는 세션입니다.")
    return ResultView(
        session_id=state.session_id,
        status=state.status,
        result=label_result(state.result, labels),
        validation=state.validation,
        stale=state.result_stale,
    )
