"""API 요청·응답 계약. 프론트 타입(frontend/src/api/schema.d.ts)은 이 파일에서 생성된다.

내부 세션 상태(trace, 프롬프트, 정책 규칙)는 여기에 싣지 않는다.
"""
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.contract import ContractModel
from app.core.results import CardType, EvidenceRecord, ResultSection, ValidationReport, VersionReason
from app.core.state import AnswerType, CoachingMode, InfoSource, Question, SessionStatus
from app.harness.flow import FlowItem
from app.harness.policy import FieldKind


class ErrorBody(ContractModel):
    """모든 오류 응답 본문(404·405·422·500·502). detail은 사용자에게 보여 줄 한국어 문장이다."""

    detail: str


class RequestErrorItem(ContractModel):
    loc: list[str | int]
    msg: str
    type: str


class RequestErrorBody(ErrorBody):
    """422 본문. errors는 DEBUG=true일 때만 실리는 개발용 상세라 선택 필드다(평소에는 키가 없다)."""

    model_config = ConfigDict(json_schema_serialization_defaults_required=False)

    errors: list[RequestErrorItem] | None = Field(
        default=None, description="DEBUG=true일 때만 채워지는 요청 검증 상세(개발용). 평소에는 없다."
    )


class TaskSummary(ContractModel):
    task_type: str
    title: str
    description: str
    heading: str
    deliverable: str
    evidence_sources: int  # 결과를 검토할 근거 자료 수(0이면 검토 버튼이 없다)


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


class EditSectionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)  # 디자인의 문구 입력 상한


class Progress(ContractModel):
    asked: int
    cap: int
    readiness: float


class SummaryItem(ContractModel):
    field: str
    label: str
    value: str
    source: InfoSource
    source_label: str
    confidence: float
    is_assumption: bool


class UnknownItem(ContractModel):
    field: str
    label: str


class SupplementItem(ContractModel):
    name: str
    label: str
    example: str
    value: str | None  # 아직 미확인이면 None


class SupplementsRequest(BaseModel):
    """{항목 이름: 값 | null}. null·빈 값이면 그 항목을 지운다."""

    values: dict[str, Annotated[str, Field(max_length=250)] | None]


class SessionView(ContractModel):
    session_id: str
    task_type: str
    mode: CoachingMode
    status: SessionStatus
    raw_input: str
    next_question: Question | None
    progress: Progress
    summary: list[SummaryItem]
    unknowns: list[UnknownItem]
    flow: list[FlowItem]  # 흐름 패널: 물어본 필드 → 지금 질문 → 예정
    supplements: list[SupplementItem]
    supplements_changed: bool  # 보완 정보가 마지막 결과에 반영되지 않았다
    can_generate: bool
    has_result: bool  # 이전에 만든 결과가 있어 GET /result로 다시 볼 수 있다
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

    sections: list[ResultSection]
    assumptions: list[LabeledAssumption]
    evidence: list[EvidenceRecord]
    full_text: str
    content: dict[str, Any]
    generated_at: datetime


class VersionSummary(ContractModel):
    version: int
    created_at: datetime
    reason: VersionReason
    saved: bool


class ResultView(ContractModel):
    session_id: str
    status: SessionStatus
    result: LabeledResult
    validation: ValidationReport | None
    stale: bool
    version: VersionSummary  # 지금 결과의 버전
    summary: list[SummaryItem]  # 이 결과를 만든 기준(그 버전의 사실·가정)
    unknowns: list[UnknownItem]  # 그 버전에서 미정이던 필드
    supplements: list[SupplementItem]  # 그 버전에 반영한 보완 정보


class VersionView(ContractModel):
    """지난 버전(또는 지금 버전) 보기. 보기 전용이다."""

    session_id: str
    version: VersionSummary
    latest: bool  # 지금 결과(마지막 버전)인지
    result: LabeledResult
    validation: ValidationReport | None
    summary: list[SummaryItem]
    unknowns: list[UnknownItem]
    supplements: list[SupplementItem]  # 그 버전에 반영한 보완 정보


class SessionSummary(ContractModel):
    """내 작업·결과물 목록의 세션 하나."""

    session_id: str
    task_type: str
    title: str  # 과제 이름
    raw_input: str
    mode: CoachingMode
    has_question: bool  # 걸린 질문이 있다(이어서 답할 수 있다)
    has_result: bool
    result_stale: bool
    latest_version: int | None  # 결과가 없으면 None
    saved_versions: list[VersionSummary]  # 저장 표시한 버전(결과물 목록에 모인다)
    updated_at: datetime


class EvidenceProposalView(ContractModel):
    title: str
    text: str
    note: str
    caution: str


class EvidenceItem(ContractModel):
    """근거 검토 화면의 자료 하나. 반영 여부는 결과의 evidence(source_id)로 안다."""

    id: str
    title: str
    publisher: str
    meta: str
    summary: str
    scope: str
    url: str
    applies_to: CardType
    record: EvidenceProposalView | None  # 결과에 붙일 점검 문구(배경 자료면 None)
