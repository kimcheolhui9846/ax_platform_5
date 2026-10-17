"""흐름 패널(질문과 답변 흐름)의 질문 목록. 세션 상태와 정책에서 만드는 순수 함수다."""
from collections.abc import Sequence
from enum import StrEnum

from app.core.contract import ContractModel
from app.core.state import AnswerType, AskedQuestion, Question, SessionState
from app.harness.base import counted_fields, unresolved_fields
from app.harness.policy import FieldPolicy, TaskPolicy


class FlowStatus(StrEnum):
    ANSWERED = "answered"  # 값을 정했다
    CURRENT = "current"  # 지금 걸려 있는 질문
    UPCOMING = "upcoming"  # 앞으로 물을 예정(정책 순서, 남은 질문 수만큼)
    SKIPPED = "skipped"  # '아직 모르겠어요'로 미정
    PAUSED = "paused"  # '다른 예시 보기' 중에 결과를 먼저 만들어 멈춘 필드. 이어 가면 다시 묻는다


class FlowItem(ContractModel):
    field: str
    label: str
    text: str
    status: FlowStatus
    answer: str | None  # 정한 값. 그 밖의 상태면 None
    # 현재 질문이거나 답한(미정·멈춤 포함) 질문. 이 질문의 question_id로 답을 고친다(PATCH). 예정이면 None
    question: Question | None


_VALUE_ANSWERS = (AnswerType.OPTION, AnswerType.FREE_TEXT)


def plan_flow(policy: TaskPolicy, state: SessionState, remaining: int) -> list[FlowItem]:
    """[순수] 물어본 필드(처음 물은 순서) → 지금 질문 → 앞으로 물을 필드(정책 순서).

    remaining은 하네스가 아직 더 물을 수 있는 기본 질문 수다(BaseHarness.questions_left). 지금 질문이 아직
    상한에 세지 않은 필드면 그 한 자리를 쓴다. 이미 센 필드(멈춘 사다리 필드)는 자리를 쓰지 않는다.
    정책에 없는 필드(정책이 바뀌어 사라진 필드)는 건너뛴다.
    """
    fields = {f.name: f for f in policy.fields}
    pending = state.pending_question
    current = pending.field if pending is not None else None
    items = [
        _asked_item(fields[name], state)
        for name in _asked_order(state.asked_questions)
        if name != current and name in fields
    ]
    if pending is not None and pending.field in fields:
        items.append(
            FlowItem(
                field=pending.field,
                label=fields[pending.field].label,
                text=pending.text,
                status=FlowStatus.CURRENT,
                answer=None,
                question=pending,
            )
        )
    counted = counted_fields(state.asked_questions)
    uncounted_current = pending is not None and pending.field not in counted
    slots = max(remaining - (1 if uncounted_current else 0), 0)
    waiting = [
        f
        for f in unresolved_fields(policy.fields, state.facts, state.unknowns)
        if f.name != current and f.name not in counted
    ]
    items.extend(_upcoming_item(f) for f in waiting[:slots])
    return items


def _asked_order(records: Sequence[AskedQuestion]) -> list[str]:
    """답한 기록이 있는 필드를 처음 답한 순서로."""
    order: list[str] = []
    for record in records:
        if record.answer_type is not None and record.question.field not in order:
            order.append(record.question.field)
    return order


def _asked_item(field: FieldPolicy, state: SessionState) -> FlowItem:
    """답한 필드 하나. 값이 있으면 그 값을 정한 질문, 미정이면 미정으로 둔 질문, 멈췄으면 마지막으로 답한 질문을 싣는다."""
    records = [
        r for r in state.asked_questions if r.question.field == field.name and r.answer_type is not None
    ]
    if field.name in state.facts:
        holder = next(
            (r for r in reversed(records) if r.answer_type in _VALUE_ANSWERS and not r.superseded), records[-1]
        )
        return FlowItem(
            field=field.name,
            label=field.label,
            text=holder.question.text,
            status=FlowStatus.ANSWERED,
            answer=state.facts[field.name].value,
            question=holder.question,
        )
    if field.name in state.unknowns:
        holder = next((r for r in reversed(records) if r.answer_type is AnswerType.SKIP), records[-1])
        return FlowItem(
            field=field.name,
            label=field.label,
            text=holder.question.text,
            status=FlowStatus.SKIPPED,
            answer=None,
            question=holder.question,
        )
    holder = records[-1]
    return FlowItem(
        field=field.name,
        label=field.label,
        text=holder.question.text,
        status=FlowStatus.PAUSED,
        answer=None,
        question=holder.question,
    )


def _upcoming_item(field: FieldPolicy) -> FlowItem:
    return FlowItem(
        field=field.name,
        label=field.label,
        text=field.question,
        status=FlowStatus.UPCOMING,
        answer=None,
        question=None,
    )
