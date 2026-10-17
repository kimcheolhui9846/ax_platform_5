"""생성 결과와 검증 리포트. 모든 과제가 공유하는 결과 래퍼다."""
from datetime import datetime, timezone
from enum import StrEnum
from collections.abc import Sequence
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.contract import ContractModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CardType(StrEnum):
    DIAGNOSIS = "diagnosis"
    SUGGESTION = "suggestion"
    ACTION = "action"


class VersionReason(StrEnum):
    """결과 버전이 생긴 까닭. 보완·근거 반영은 그 기능이 생길 때 더한다."""

    FIRST = "first"  # 첫 초안
    REGENERATE = "regenerate"  # 다시 만든 초안
    EDIT = "edit"  # 문구 수정


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


class TextBlock(ContractModel):
    """결과 섹션의 글 블록. 이미지 블록(묶음 3b)과 type으로 구분한다."""

    type: Literal["text"] = "text"
    text: str


class ResultSection(ContractModel):
    """결과 문서의 섹션 하나(진단·제안·실행 과제). 내용은 블록 목록이다."""

    order: int
    heading: str
    kind: CardType
    blocks: list[TextBlock]


def sections_from_cards(cards: Sequence[ResultCard]) -> list[ResultSection]:
    """[순수] LLM이 쓴 카드를 순서대로 섹션으로 바꾼다(본문은 글 블록 하나)."""
    return [
        ResultSection(order=c.order, heading=c.title, kind=c.card_type, blocks=[TextBlock(text=c.body)])
        for c in sorted(cards, key=lambda c: c.order)
    ]


def section_text(section: ResultSection) -> str:
    """[순수] 섹션의 글 블록을 이어 붙인 본문."""
    return "\n\n".join(block.text for block in section.blocks if block.type == "text")


def compose_full_text(sections: Sequence[ResultSection]) -> str:
    """[순수] 섹션들로 다시 만든 완성본(문구를 고친 뒤 검증·복사에 쓴다)."""
    return "\n\n".join(f"{s.heading}\n{section_text(s)}" for s in sections)


class GenerationResult(ContractModel):
    """세션에 저장되는 결과. content는 과제별 스키마를 통과한 값의 dict다."""

    sections: list[ResultSection]
    assumptions: list[ResultAssumption] = Field(default_factory=list)
    full_text: str
    content: dict[str, Any]
    generated_at: datetime = Field(default_factory=utcnow)

    @model_validator(mode="before")
    @classmethod
    def _sections_from_legacy_cards(cls, data: Any) -> Any:
        """섹션이 생기기 전에 저장한 결과(cards)는 섹션으로 읽는다."""
        if isinstance(data, dict) and "sections" not in data and "cards" in data:
            cards = [ResultCard.model_validate(c) for c in data["cards"]]
            data = {k: v for k, v in data.items() if k != "cards"} | {"sections": sections_from_cards(cards)}
        return data


def with_section_text(result: GenerationResult, order: int, text: str) -> GenerationResult | None:
    """[순수] 섹션 하나의 글을 바꾼 새 결과(복사본). 그 섹션이 없으면 None. 완성본(full_text)도 다시 만든다."""
    if not any(s.order == order for s in result.sections):
        return None
    sections = [
        s.model_copy(update={"blocks": [TextBlock(text=text)]}) if s.order == order else s.model_copy(deep=True)
        for s in result.sections
    ]
    return result.model_copy(deep=True, update={"sections": sections, "full_text": compose_full_text(sections)})


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
