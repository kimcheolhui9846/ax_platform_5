"""브랜딩 결과물. 이 모델이 하네스 설계의 기준점이다."""
from pydantic import BaseModel, Field


class BrandingContent(BaseModel):
    positioning: str = Field(description="누구에게 어떤 점에서 다른 브랜드인지")
    brand_keywords: list[str] = Field(description="브랜드를 대표하는 키워드")
    tone_and_manner: str = Field(description="말투와 표현 방식")
    naming_directions: list[str] = Field(description="네이밍 방향 제안")
    slogan_directions: list[str] = Field(description="슬로건 방향 제안")
