"""세션 상태. 설계서 10.2(세션 상태)와 12장(사실·가정 분리)을 그대로 옮긴 모델이다."""
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.contract import ContractModel
from app.core.results import GenerationResult, ValidationReport, utcnow


class SessionStatus(StrEnum):
    DRAFTING = "drafting"
    CLARIFYING = "clarifying"
    CONFIRMING = "confirming"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISING = "revising"


class CoachingMode(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    PRECISE = "precise"


class InfoSource(StrEnum):
    USER_FREE_TEXT = "user_free_text"
    USER_SELECTED_AI_OPTION = "user_selected_ai_option"
    PREVIOUS_TASK = "previous_task"
    AI_ASSUMPTION = "ai_assumption"
    DEFAULT = "default"


class AnswerType(StrEnum):
    OPTION = "option"
    FREE_TEXT = "free_text"
    DONT_KNOW = "dont_know"
    SKIP = "skip"


class InfoItem(BaseModel):
    value: str
    source: InfoSource
    confidence: float = 1.0
    updated_at: datetime = Field(default_factory=utcnow)


class Assumption(InfoItem):
    reason: str = ""
    requires_confirmation: bool = True


class Conflict(BaseModel):
    field: str
    values: list[str]


class QuestionOption(ContractModel):
    id: str
    label: str
    ai_suggested: bool = False


class Question(ContractModel):
    question_id: str = Field(default_factory=lambda: f"q_{uuid4().hex[:10]}")
    field: str
    text: str
    options: list[QuestionOption] = Field(default_factory=list)
    multi_select: bool = False
    level: int = 0  # 0 = 기본 질문, 1 이상 = '모르겠어요' 사다리 단계
    is_ai_proposal: bool = False


class Answer(BaseModel):
    question_id: str
    answer_type: AnswerType
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class AskedQuestion(BaseModel):
    question: Question
    answer_type: AnswerType | None = None
    value: str | None = None
    answered_at: datetime | None = None
    # 같은 필드에 나중 답(또는 수정)이 값을 정했으면 True. 지금 값은 언제나 facts가 기준이다.
    superseded: bool = False


class TraceEntry(ContractModel):
    stage: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None  # 제공자 이름(mock, claude 등)
    model: str | None = None  # 실제로 응답한 모델 id. 호출이 실패하면 None
    usage: dict[str, int] = Field(default_factory=dict)
    at: datetime = Field(default_factory=utcnow)


class HarnessProfile(BaseModel):
    """설계서 6.4 하네스 설정값. 지금은 기본값만 쓰고, 온보딩 설문(ON)이 생기면 채운다."""

    prompt_skill: str = "beginner"
    coaching_style: str = "step_by_step"
    preferred_detail: str = "medium"
    feedback_tone: str = "balanced"
    result_format: str = "mobile_cards"
    alternative_count: int = 3
    assumption_policy: str = "ask_first"
    question_batch_size: int = 1
    use_examples: bool = True


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:12]}")
    task_type: str
    mode: CoachingMode = CoachingMode.STANDARD
    status: SessionStatus = SessionStatus.DRAFTING
    profile: HarnessProfile = Field(default_factory=HarnessProfile)
    raw_input: str = ""
    facts: dict[str, InfoItem] = Field(default_factory=dict)
    assumptions: dict[str, Assumption] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    dont_know_levels: dict[str, int] = Field(default_factory=dict)  # 모르겠어요 사다리 현재 단계
    conflicts: list[Conflict] = Field(default_factory=list)
    asked_questions: list[AskedQuestion] = Field(default_factory=list)
    pending_question: Question | None = None
    readiness: float = 0.0
    result: GenerationResult | None = None
    result_stale: bool = False
    validation: ValidationReport | None = None
    trace: list[TraceEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def find_asked(self, question_id: str) -> AskedQuestion | None:
        return next(
            (a for a in self.asked_questions if a.question.question_id == question_id), None
        )
