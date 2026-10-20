"""요청 본문의 공통 부모. 모든 요청 모델이 상속한다."""
from typing import Any

from pydantic import BaseModel, model_validator


def strip_nul(value: Any) -> Any:
    """문자열 안의 NUL(\x00)을 빼며 목록·사전 안쪽까지 훑는다. Postgres JSONB는 NUL을 받지 않는다."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [strip_nul(item) for item in value]
    if isinstance(value, dict):
        return {strip_nul(key): strip_nul(item) for key, item in value.items()}
    return value


class RequestModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _strip_nul(cls, data: Any) -> Any:
        return strip_nul(data)
