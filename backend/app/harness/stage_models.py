"""LLM 단계별 응답 형태. Provider에 response_model로 넘긴다."""
from pydantic import BaseModel, Field

from app.core.results import ValidationIssue


class ExtractedField(BaseModel):
    field: str = Field(description="policy 필드 이름")
    value: str = Field(description="입력에서 찾은 값")


class Diagnosis(BaseModel):
    extracted: list[ExtractedField] = Field(
        default_factory=list, description="입력에서 분명히 확인되는 항목"
    )
    ambiguous: list[str] = Field(default_factory=list, description="뜻이 모호한 표현")


class GeneratedQuestion(BaseModel):
    text: str = Field(description="더 쉬운 질문 문구")
    options: list[str] = Field(default_factory=list, description="고를 수 있는 선택지")


class ProposedValues(BaseModel):
    text: str = Field(description="후보를 고르게 하는 안내 문장")
    candidates: list[str] = Field(description="AI가 제안하는 후보 값")


class LLMReview(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list, description="발견한 문제")
