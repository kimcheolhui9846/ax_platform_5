"""내부 상태 → API 응답 변환. 프론트가 바로 그릴 수 있는 값만 담는다. 모두 순수 함수다."""
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet

from app.core.messages import GENERATION_FAILED_MESSAGE
from app.core.results import GenerationResult, ResultAssumption
from app.core.state import (
    Assumption,
    CarriedContext,
    CoachingMode,
    InfoItem,
    ResultVersion,
    SESSION_NAME_MAX,
    SessionState,
    SessionStatus,
    source_label,
)
from app.harness.base import BaseHarness, supplements_changed
from app.harness.evidence import EvidenceSource
from app.harness.flow import plan_flow
from app.harness.policy import FieldPolicy, SupplementField, TaskPolicy
from app.schemas.coaching import (
    ContextItem,
    EvidenceItem,
    EvidenceProposalView,
    FieldSummary,
    LabeledAssumption,
    LabeledResult,
    ModeInfo,
    Progress,
    ResultView,
    SessionContext,
    SessionSummary,
    SessionView,
    SummaryItem,
    SupplementItem,
    TaskForm,
    TaskSummary,
    UnknownItem,
    VersionSummary,
    VersionView,
)


def to_task_summary(policy: TaskPolicy, evidence_sources: int) -> TaskSummary:
    return TaskSummary(
        task_type=policy.task_type,
        title=policy.title,
        description=policy.description,
        heading=policy.heading,
        deliverable=policy.deliverable,
        evidence_sources=evidence_sources,
    )


def to_evidence_items(sources: Sequence[EvidenceSource]) -> list[EvidenceItem]:
    """[순수] 근거 자료를 화면용으로(점검 문구는 그대로 옮긴다)."""
    return [
        EvidenceItem(
            id=s.id,
            title=s.title,
            publisher=s.publisher,
            meta=s.meta,
            summary=s.summary,
            scope=s.scope,
            url=s.url,
            applies_to=s.applies_to,
            record=EvidenceProposalView(title=s.record.title, text=s.record.text, note=s.record.note, caution=s.record.caution) if s.record else None,
        )
        for s in sources
    ]


def to_task_form(policy: TaskPolicy) -> TaskForm:
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
    private: AbstractSet[str],
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
                source_label=source_label(item.source),
                confidence=item.confidence,
                is_assumption=f.name not in facts,
                private=f.name in private,
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
        sections=result.sections,
        assumptions=label_assumptions(result.assumptions, labels),
        evidence=result.evidence,
        full_text=result.full_text,
        content=result.content,
        generated_at=result.generated_at,
    )


def session_error(status: SessionStatus) -> str | None:
    """[순수] 사용자에게 보일 오류 문구. 저장하지 않고 상태에서 만든다(FAILED는 생성 실패뿐이다)."""
    return GENERATION_FAILED_MESSAGE if status is SessionStatus.FAILED else None


def to_session_context(context: CarriedContext, labels: Mapping[str, str]) -> SessionContext:
    """[순수] 가져온 기준에 화면용 라벨(이 과제의 필드 라벨)을 붙인다."""
    return SessionContext(
        session_id=context.session_id,
        task_type=context.task_type,
        version=context.version,
        title=context.title,
        summary=context.summary,
        items=[
            ContextItem(field=i.field, label=labels.get(i.field, i.field), value=i.value, private=i.private)
            for i in context.items
        ],
    )


def to_session_view(state: SessionState, harness: BaseHarness) -> SessionView:
    """can_generate는 비동기 생성을 도입할 때를 위해 남겨 둔 값이다(지금 생성은 동기라 항상 true)."""
    private = harness.private(state)
    return SessionView(
        session_id=state.session_id,
        task_type=state.task_type,
        mode=state.mode,
        status=state.status,
        name=session_name(state),
        raw_input=state.raw_input,
        next_question=state.pending_question,
        progress=Progress(
            asked=harness.asked_count(state),
            cap=harness.question_cap(state),
            readiness=state.readiness,
        ),
        summary=build_summary(harness.policy.fields, state.facts, state.assumptions, private),
        unknowns=label_unknowns(state.unknowns, harness.policy.labels),
        flow=plan_flow(harness.policy, state, harness.questions_left(state)),
        supplements=supplement_items(harness.policy.supplement_fields, state.supplements, private),
        private_names=sorted(private),
        supplements_changed=supplements_changed(state.supplements, state.versions[-1] if state.versions else None),
        context=to_session_context(state.context, harness.policy.labels) if state.context else None,
        can_generate=state.status is not SessionStatus.GENERATING,
        has_result=state.result is not None,
        result_stale=state.result_stale,
        error=session_error(state.status),
    )


def version_summary(version: ResultVersion) -> VersionSummary:
    return VersionSummary(
        version=version.version, created_at=version.created_at, reason=version.reason, saved=version.saved
    )


def field_labels(fields: Sequence[FieldPolicy]) -> dict[str, str]:
    """[순수] 필드 이름 → 화면용 라벨."""
    return {f.name: f.label for f in fields}


def supplement_items(
    fields: Sequence[SupplementField], values: Mapping[str, InfoItem], private: AbstractSet[str]
) -> list[SupplementItem]:
    """[순수] 정책 순서대로 보완 항목과 지금 값(없으면 None)."""
    return [
        SupplementItem(
            name=f.name,
            label=f.label,
            example=f.example,
            value=values[f.name].value if f.name in values else None,
            private=f.name in private,
        )
        for f in fields
    ]


def to_result_view(
    state: SessionState, fields: Sequence[FieldPolicy], supplement_fields: Sequence[SupplementField]
) -> ResultView:
    """[순수] 지금 결과. 기준(summary·unknowns)은 지금 세션이 아니라 이 결과를 만든 버전의 것이다."""
    if state.result is None or not state.versions:
        raise ValueError("생성된 결과가 없는 세션입니다.")
    latest = state.versions[-1]
    labels = field_labels(fields)
    return ResultView(
        session_id=state.session_id,
        status=state.status,
        result=label_result(state.result, labels),
        validation=state.validation,
        stale=state.result_stale,
        version=version_summary(latest),
        summary=build_summary(fields, latest.facts, latest.assumptions, frozenset(latest.private or ())),
        unknowns=label_unknowns(latest.unknowns, labels),
        supplements=supplement_items(supplement_fields, latest.supplements, frozenset(latest.private or ())),
    )


def to_version_view(
    state: SessionState,
    version: ResultVersion,
    fields: Sequence[FieldPolicy],
    supplement_fields: Sequence[SupplementField],
) -> VersionView:
    """[순수] 버전 하나 보기(그 버전의 결과와 기준)."""
    labels = field_labels(fields)
    return VersionView(
        session_id=state.session_id,
        version=version_summary(version),
        latest=version.version == state.versions[-1].version,
        result=label_result(version.result, labels),
        validation=version.validation,
        summary=build_summary(fields, version.facts, version.assumptions, frozenset(version.private or ())),
        unknowns=label_unknowns(version.unknowns, labels),
        supplements=supplement_items(supplement_fields, version.supplements, frozenset(version.private or ())),
    )


def session_name(state: SessionState) -> str:
    """[순수] 작업 이름. 붙인 이름이 있으면 그것, 없으면 처음 요청 글의 첫 줄(앞뒤 공백 제거) 40자."""
    if state.name:
        return state.name
    lines = state.raw_input.strip().splitlines()
    return lines[0].strip()[:SESSION_NAME_MAX] if lines else ""


def to_session_summary(state: SessionState, title: str) -> SessionSummary:
    """[순수] 목록에 보일 세션 요약. title은 과제 이름이다."""
    return SessionSummary(
        session_id=state.session_id,
        task_type=state.task_type,
        title=title,
        name=session_name(state),
        raw_input=state.raw_input,
        mode=state.mode,
        has_question=state.pending_question is not None,
        has_result=state.result is not None,
        result_stale=state.result_stale,
        latest_version=state.versions[-1].version if state.versions else None,
        saved_versions=[version_summary(v) for v in state.versions if v.saved],
        updated_at=state.updated_at,
    )
