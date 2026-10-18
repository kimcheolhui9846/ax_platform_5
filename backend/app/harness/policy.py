"""과제별 policy.yaml을 읽고 검증한다. fields의 순서가 곧 고정 질문 우선순위다.

모르는 키(오타)는 조용히 무시하지 않고 읽을 때 거부한다(extra="forbid").
"""
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from app.core.state import CoachingMode


class FieldKind(StrEnum):
    MUST_CONFIRM = "must_confirm"  # 없으면 반드시 묻는다
    AI_SUGGEST = "ai_suggest"  # 후보를 제시하고 고르게 한다
    DEFAULT = "default"  # 기본값을 자동 적용하고 묻지 않는다


class LadderStep(BaseModel):
    """'다른 예시 보기' 사다리의 고정 질문. 비교·선택형 단계라 필드와 달리 기본은 하나만 고른다."""

    model_config = ConfigDict(extra="forbid")

    question: str
    options: list[str] = Field(default_factory=list)
    multi_select: bool = False


class SupplementField(BaseModel):
    """결과를 만든 뒤 사용자가 채우는 미확인 정보 항목(필드와 따로다. 질문하지 않는다)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    example: str = ""


class FieldPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    label: str
    kind: FieldKind = FieldKind.MUST_CONFIRM
    weight: float = Field(default=1.0, gt=0)
    question: str = ""
    options: list[str] = Field(default_factory=list)
    multi_select: bool = False
    easier_questions: list[LadderStep] = Field(default_factory=list)
    default: str | None = None

    @model_validator(mode="after")
    def _check_kind(self) -> "FieldPolicy":
        if self.kind is FieldKind.DEFAULT and self.default is None:
            raise ValueError(f"{self.name}: kind=default이면 default 값이 필요합니다")
        if self.kind is not FieldKind.DEFAULT and not self.question:
            raise ValueError(f"{self.name}: 질문 문구(question)가 필요합니다")
        return self


def _default_caps() -> dict[CoachingMode, PositiveInt]:
    return {CoachingMode.QUICK: 3, CoachingMode.STANDARD: 5, CoachingMode.PRECISE: 10}


class TaskPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: str
    title: str
    description: str = ""
    heading: str = Field(min_length=1)  # 홈 과제 카드의 큰 문구(사용자가 하고 싶은 말)
    deliverable: str = Field(min_length=1)  # 완성할 결과물 이름(홈·답변 확인·결과 화면)
    input_placeholder: str = ""
    input_examples: list[str] = Field(default_factory=list)
    raw_input_field: str | None = None  # 첫 한 줄 입력을 사실로 둘 필드
    readiness_threshold: float = Field(default=0.7, ge=0, le=1)
    question_caps: dict[CoachingMode, PositiveInt] = Field(default_factory=_default_caps)
    max_easier_level: int = Field(default=4, ge=1)  # 이 단계부터 AI 후보 제안
    llm_validation: bool = False  # 생성 후 LLM 검토 호출 (비용 때문에 기본 꺼짐)
    image_generation: bool = False  # 생성마다 참고 이미지 한 장 (비용 때문에 기본 꺼짐)
    fields: list[FieldPolicy]
    supplement_fields: list[SupplementField] = Field(default_factory=list)
    private_fields: list[str] = Field(default_factory=list)  # AI에 보내지 않는 기본 항목(필드·보완 항목 이름)
    carry_over: dict[str, str] = Field(default_factory=dict)  # 이전 과제 이름 → 이 과제 필드(같은 이름은 적지 않아도 가져온다)
    rules: list[str] = Field(default_factory=list)  # 금지·주의 규칙

    @model_validator(mode="after")
    def _check_fields(self) -> "TaskPolicy":
        names = [f.name for f in self.fields]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"필드 이름이 중복됩니다: {', '.join(duplicates)}")
        if self.raw_input_field is not None and self.raw_input_field not in names:
            raise ValueError(f"raw_input_field '{self.raw_input_field}'가 fields에 없습니다")
        missing = sorted(set(CoachingMode) - set(self.question_caps))
        if missing:
            raise ValueError(f"question_caps에 모드가 빠졌습니다: {', '.join(m.value for m in missing)}")
        unreachable = [f.name for f in self.fields if len(f.easier_questions) >= self.max_easier_level]
        if unreachable:
            raise ValueError(
                f"easier_questions는 max_easier_level({self.max_easier_level})보다 적어야 합니다. "
                f"그 단계부터는 AI 후보 제안이 대신해 닿지 않습니다: {', '.join(unreachable)}"
            )
        supplement_names = [s.name for s in self.supplement_fields]
        repeated = sorted({n for n in supplement_names if supplement_names.count(n) > 1})
        if repeated:
            raise ValueError(f"보완 항목 이름이 중복됩니다: {', '.join(repeated)}")
        clashes = sorted(set(supplement_names) & set(names))
        if clashes:
            raise ValueError(f"보완 항목 이름이 필드와 겹칩니다: {', '.join(clashes)}")
        unknown_private = sorted(set(self.private_fields) - set(names) - set(supplement_names))
        if unknown_private:
            raise ValueError(f"private_fields에 모르는 이름이 있습니다: {', '.join(unknown_private)}")
        strays = sorted(set(self.carry_over.values()) - set(names))
        if strays:
            raise ValueError(f"carry_over의 대상이 필드가 아닙니다: {', '.join(strays)}")
        return self

    def field(self, name: str) -> FieldPolicy:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    @property
    def labels(self) -> dict[str, str]:
        return {f.name: f.label for f in self.fields}

    @property
    def supplement_labels(self) -> dict[str, str]:
        return {s.name: s.label for s in self.supplement_fields}


def load_policy(path: Path) -> TaskPolicy:
    with path.open(encoding="utf-8") as fp:
        return TaskPolicy.model_validate(yaml.safe_load(fp))
