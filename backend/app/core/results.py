"""생성 결과와 검증 리포트. 모든 과제가 공유하는 결과 래퍼다."""
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.core.contract import ContractModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CardType(StrEnum):
    DIAGNOSIS = "diagnosis"
    SUGGESTION = "suggestion"
    ACTION = "action"


class VersionReason(StrEnum):
    """결과 버전이 생긴 까닭. 보완·문구 수정·근거 반영은 그 기능이 생길 때(묶음 3) 더한다."""

    FIRST = "first"  # 첫 초안
    REGENERATE = "regenerate"  # 다시 만든 초안


class ResultCard(ContractModel):
    card_type: CardType = Field(description="카드 유형: 진단·제안·실행 과제")
    title: str = Field(description="카드 제목")
    body: str = Field(description="카드 본문")
    order: int = Field(description="표시 순서")


class ResultAssumption(ContractModel):
    field: str = Field(description="AI가 보완한 항목의 필드 이름")
    value: str = Field(description="AI가 가정한 값")
    reason: str = Field(default="", description="그렇게 가정한 이유")
    requires_confirmation: bool = Field(default=True, description="사용자 확인이 필요한지")


ContentT = TypeVar("ContentT", bound=BaseModel)


class TaskResult(BaseModel, Generic[ContentT]):
    """LLM이 채워야 하는 결과 형태. content 자리에 과제별 output_schema가 들어간다."""

    cards: list[ResultCard] = Field(description="모바일 결과 카드 목록")
    assumptions: list[ResultAssumption] = Field(
        default_factory=list, description="AI가 가정으로 보완한 항목"
    )
    full_text: str = Field(description="복사·저장용 완성본")
    content: ContentT


class GenerationResult(ContractModel):
    """세션에 저장되는 결과. content는 과제별 스키마를 통과한 값의 dict다."""

    cards: list[ResultCard]
    assumptions: list[ResultAssumption] = Field(default_factory=list)
    full_text: str
    content: dict[str, Any]
    generated_at: datetime = Field(default_factory=utcnow)


class ValidationIssue(ContractModel):
    rule: str = Field(description="어긴 규칙 이름")
    message: str = Field(description="사용자·개발자가 읽을 설명")
    severity: Literal["warning", "error"] = Field(default="warning", description="심각도")


class ValidationReport(ContractModel):
    # passed(computed_field)가 입력·출력 스키마를 갈라놓지 않도록 항상 직렬화 스키마로 낸다.
    model_config = ConfigDict(json_schema_mode_override="serialization")

    issues: list[ValidationIssue] = Field(default_factory=list)

    @computed_field
    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)
