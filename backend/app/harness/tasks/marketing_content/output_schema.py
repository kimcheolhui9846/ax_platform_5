"""마케팅 콘텐츠 결과물. 이 모델이 하네스 설계의 기준점이다."""
from typing import Literal

from pydantic import BaseModel, Field


class ContentPiece(BaseModel):
    format: Literal["sns_post", "ad_copy", "detail_page", "shortform_script"] = Field(
        description="콘텐츠 형식: SNS 글·광고 카피·상세페이지·숏폼 대본"
    )
    title: str = Field(description="콘텐츠 제목 또는 첫 문장")
    body: str = Field(description="콘텐츠 본문")


class MarketingContent(BaseModel):
    channel: str = Field(description="게시할 채널")
    key_message: str = Field(description="전달할 핵심 메시지")
    contents: list[ContentPiece] = Field(description="채널에 맞춘 콘텐츠")
    cta: str = Field(description="행동 유도 문구")
