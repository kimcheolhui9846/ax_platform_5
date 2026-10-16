"""상품기획 결과물. 이 모델이 하네스 설계의 기준점이다."""
from pydantic import BaseModel, Field


class ProductPlanningContent(BaseModel):
    value_proposition: str = Field(description="고객 문제를 해결하는 가치제안")
    core_features: list[str] = Field(description="핵심 기능 또는 구성")
    mvp_scope: str = Field(description="가장 작게 시작할 MVP 범위")
    price_direction: str = Field(description="가격 방향과 확인할 기준")
    validation_experiments: list[str] = Field(description="상품 가설을 검증할 실험")
