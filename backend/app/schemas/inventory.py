"""재고 API 요청·응답 스키마. 저장 모델은 app/inventory/models.py에 있다."""
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.inventory.models import ItemKind, MockOutcome, Procurement, Quantity, SignedQuantity

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
OptionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]


class ItemDraft(BaseModel):
    """품목 하나 등록(S01 일괄 등록의 한 줄, S02 개별 등록). quantity를 적으면 그 수량으로 실사를 남긴다."""

    name: Name
    option: OptionText | None = None
    kind: ItemKind
    unit: Unit
    procurement: Procurement = Procurement.PURCHASE
    supplier_id: str | None = None
    quantity: Quantity | None = None


class BulkItemsRequest(BaseModel):
    items: list[ItemDraft] = Field(min_length=1, max_length=200)


class ItemPatch(BaseModel):
    """보낸 필드만 바꾼다. name·kind·unit·procurement·archived는 null이면 그대로, option·supplier_id는 null이면 비운다."""

    name: Name | None = None
    option: OptionText | None = None
    kind: ItemKind | None = None
    unit: Unit | None = None
    procurement: Procurement | None = None
    supplier_id: str | None = None
    archived: bool | None = None


class SupplierDraft(BaseModel):
    name: Name
    mock_outcome: MockOutcome = MockOutcome.ACCEPT


class SupplierPatch(BaseModel):
    """보낸 필드만 바꾼다. null이면 그대로."""

    name: Name | None = None
    mock_outcome: MockOutcome | None = None


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Adjustment(BaseModel):
    """S05-check 조정: 마지막 실사에 더하거나 뺀다. 사유 필수, 0은 받지 않는다."""

    item_id: str
    delta: SignedQuantity
    reason: Reason

    @field_validator("delta")
    @classmethod
    def _not_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("조정 값은 0일 수 없습니다.")
        return value


class CloseCheckRequest(BaseModel):
    counts: dict[str, Quantity] = Field(default_factory=dict)


class CloseRequest(BaseModel):
    """S05 하루 마감. counts에 없는 품목은 미입력. confirmed는 이상 수량을 확인한 품목 id."""

    close_date: date
    counts: dict[str, Quantity] = Field(default_factory=dict)
    adjustments: list[Adjustment] = Field(default_factory=list)
    confirmed: list[str] = Field(default_factory=list)
