"""API 응답에 실리는 모델의 공통 부모.

기본값이 있는 필드도 직렬화 스키마에서는 필수로 표시한다. 응답에는 항상 채워져 나가므로
생성되는 프론트 타입이 선택 필드(`field?:`)로 느슨해지지 않는다.
"""
from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)
