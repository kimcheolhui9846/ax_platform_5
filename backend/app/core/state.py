"""세션 상태. 설계서 10.2(세션 상태)와 12장(사실·가정 분리)을 그대로 옮긴 모델이다."""
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.core.contract import ContractModel
from app.core.results import GenerationResult, ValidationReport, VersionReason, utcnow


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


# 정보 출처의 한국어 라벨. 프롬프트와 API 응답(SummaryItem.source_label)이 함께 쓴다.
SOURCE_LABELS: dict[InfoSource, str] = {
    InfoSource.USER_FREE_TEXT: "직접 입력",
    InfoSource.USER_SELECTED_AI_OPTION: "선택지에서 고름",
    InfoSource.PREVIOUS_TASK: "이전 과제",
    InfoSource.AI_ASSUMPTION: "AI 가정",
    InfoSource.DEFAULT: "기본값",
}


def source_label(source: InfoSource) -> str:
    """[순수] 정보 출처를 사람이 읽는 한국어로."""
    return SOURCE_LABELS[source]


class AnswerType(StrEnum):
    OPTION = "option"
    FREE_TEXT = "free_text"
    EASIER = "easier"
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
    level: int = 0  # 0 = 기본 질문, 1 이상 = '다른 예시 보기' 사다리 단계
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
    # trace·디버깅용 이력 표시다. 아직 API 응답은 이 값을 쓰지 않는다(이전 답 목록 UI가 생기면 쓴다).
    superseded: bool = False


class ResultVersion(BaseModel):
    """결과가 바뀔 때마다 하나씩 쌓는 기록. 마지막 버전의 결과가 지금 결과(SessionState.result)다.

    그때의 사실·가정·미정을 복사해 둔다. 나중에 이 버전을 열면 그 기준으로 보여 준다.
    """

    version: int
    created_at: datetime
    reason: VersionReason
    result: GenerationResult
    validation: ValidationReport | None = None
    facts: dict[str, InfoItem] = Field(default_factory=dict)
    assumptions: dict[str, Assumption] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    saved: bool = False  # 저장 표시(결과물 목록에 모인다)

    @classmethod
    def snapshot(
        cls,
        number: int,
        reason: VersionReason,
        result: GenerationResult,
        validation: ValidationReport | None,
        facts: Mapping[str, InfoItem],
        assumptions: Mapping[str, Assumption],
        unknowns: Sequence[str],
    ) -> "ResultVersion":
        """그때의 결과·검증·기준을 복사해 버전 하나를 만든다. 뒤에 세션이 바뀌어도 이 버전은 그대로다."""
        return cls(
            version=number,
            created_at=result.generated_at,
            reason=reason,
            result=result.model_copy(deep=True),
            validation=validation.model_copy(deep=True) if validation is not None else None,
            facts={name: item.model_copy() for name, item in facts.items()},
            assumptions={name: item.model_copy() for name, item in assumptions.items()},
            unknowns=list(unknowns),
        )

    def derived(
        self, number: int, reason: VersionReason, result: GenerationResult, validation: ValidationReport | None
    ) -> "ResultVersion":
        """이 버전의 기준(사실·가정·미정)을 그대로 이어받고 결과만 바꾼 새 버전(문구 수정)."""
        return ResultVersion.snapshot(number, reason, result, validation, self.facts, self.assumptions, self.unknowns)


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
    owner_id: str = ""  # 익명 사용자 ID(X-Client-Id). 로그인을 붙이면 계정 ID가 된다
    task_type: str
    mode: CoachingMode = CoachingMode.STANDARD
    status: SessionStatus = SessionStatus.DRAFTING
    profile: HarnessProfile = Field(default_factory=HarnessProfile)
    raw_input: str = ""
    facts: dict[str, InfoItem] = Field(default_factory=dict)
    assumptions: dict[str, Assumption] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    easier_levels: dict[str, int] = Field(default_factory=dict)  # 다른 예시 보기 사다리 현재 단계
    conflicts: list[Conflict] = Field(default_factory=list)
    asked_questions: list[AskedQuestion] = Field(default_factory=list)
    pending_question: Question | None = None
    readiness: float = 0.0
    result: GenerationResult | None = None
    result_stale: bool = False
    validation: ValidationReport | None = None
    versions: list[ResultVersion] = Field(default_factory=list)  # 만든 결과의 기록(1부터, 마지막이 지금 결과)
    trace: list[TraceEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _version_legacy_result(self) -> "SessionState":
        """버전 기록이 생기기 전에 저장한 세션은 지금 결과를 V1로 붙인다(지금 결과 = 마지막 버전).

        그때의 기준은 남아 있지 않아 지금 세션의 사실·가정·미정으로 대신한다(개발 중에 만든 세션에만 해당하는 근사값).
        """
        if self.result is not None and not self.versions:
            self.versions = [
                ResultVersion.snapshot(
                    1, VersionReason.FIRST, self.result, self.validation, self.facts, self.assumptions, self.unknowns
                )
            ]
        return self

    def find_asked(self, question_id: str) -> AskedQuestion | None:
        return next(
            (a for a in self.asked_questions if a.question.question_id == question_id), None
        )
