"""사업계획 결과물. 이 모델이 하네스 설계의 기준점이다(필드 → 질문 → 검증이 여기서 파생)."""
from pydantic import BaseModel, Field


class BusinessPlanContent(BaseModel):
    customer_problem: str = Field(description="고객이 겪는 핵심 문제")
    target_customer: str = Field(description="가장 먼저 공략할 목표 고객")
    solution: str = Field(description="문제를 해결하는 방식")
    revenue_model: str = Field(description="수익을 내는 구조")
    risks: list[str] = Field(description="주요 위험과 불확실성")
    validation_plan: list[str] = Field(description="가설을 검증할 다음 행동")
