"""IR 피치덱 결과물. 이 모델이 하네스 설계의 기준점이다(필드 → 질문 → 검증이 여기서 파생)."""
from typing import Literal

from pydantic import BaseModel, Field

SlideType = Literal[
    "cover", "problem", "solution", "market", "business_model", "traction", "competition", "team", "financials", "ask"
]


class PitchSlide(BaseModel):
    slide_type: SlideType = Field(
        description="슬라이드 종류: 표지·문제·해결·시장·비즈니스 모델·성과·경쟁·팀·재무 계획·투자 요청"
    )
    headline: str = Field(description="슬라이드 한 장의 핵심 주장 한 문장")
    script: str = Field(description="이 슬라이드에서 발표자가 말할 원고")


class IrPitchContent(BaseModel):
    one_liner: str = Field(description="투자자에게 회사를 한 문장으로 소개")
    slides: list[PitchSlide] = Field(min_length=5, max_length=12, description="발표 순서대로 놓은 슬라이드")
    ask: str = Field(description="투자 요청: 원하는 투자 형태와 자금 사용 계획")
    investor_questions: list[str] = Field(description="투자자가 물을 만한 질문과 답을 준비할 것")
