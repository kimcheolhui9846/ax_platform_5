"""API 요청·응답 계약. 프론트 타입(frontend/src/api/schema.d.ts)은 이 파일에서 생성된다.

내부 세션 상태(trace, 프롬프트, 정책 규칙)는 여기에 싣지 않는다.
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.contract import ContractModel
from app.core.results import ResultCard, ValidationReport
from app.core.state import AnswerType, CoachingMode, InfoSource, Question, SessionStatus
from app.harness.policy import FieldKind


class TaskSummary(ContractModel):
    task_type: str
    title: str
    description: str


class ModeInfo(ContractModel):
    mode: CoachingMode
    question_cap: int


class FieldSummary(ContractModel):
    name: str
    label: str
    kind: FieldKind


class TaskForm(ContractModel):
    task_type: str
    title: str
    description: str
    input_placeholder: str
    input_examples: list[str]
    modes: list[ModeInfo]
    fields: list[FieldSummary]


class CreateSessionRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=2000)
    mode: CoachingMode = CoachingMode.STANDARD


class AnswerRequest(BaseModel):
    question_id: str
    answer_type: AnswerType
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class ReviseAnswerRequest(BaseModel):
    answer_type: Literal[AnswerType.OPTION, AnswerType.FREE_TEXT]
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class Progress(ContractModel):
    asked: int
    cap: int
    readiness: float


class SummaryItem(ContractModel):
    field: str
    label: str
    value: str
    source: InfoSource
    confidence: float
    is_assumption: bool


class UnknownItem(ContractModel):
    field: str
    label: str


class SessionView(ContractModel):
    session_id: str
    task_type: str
    mode: CoachingMode
    status: SessionStatus
    next_question: Question | None
    progress: Progress
    summary: list[SummaryItem]
    unknowns: list[UnknownItem]
    can_generate: bool
    result_stale: bool
    error: str | None


class LabeledAssumption(ContractModel):
    field: str
    label: str
    value: str
    reason: str
    requires_confirmation: bool


class LabeledResult(ContractModel):
    """GenerationResult에 화면용 라벨을 붙인 것. LLM이 채우는 결과 형태(TaskResult)에는 라벨을 두지 않는다."""

    cards: list[ResultCard]
    assumptions: list[LabeledAssumption]
    full_text: str
    content: dict[str, Any]
    generated_at: datetime


class ResultView(ContractModel):
    session_id: str
    status: SessionStatus
    result: LabeledResult
    validation: ValidationReport | None
    stale: bool
