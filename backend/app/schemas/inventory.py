"""재고 API 요청·응답 스키마. 저장 모델은 app/inventory/models.py에 있다."""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.contract import ContractModel
from app.core.messages import INVENTORY_ZERO_ADJUST_MESSAGE
from app.inventory.models import (
    Close,
    InventorySettings,
    Item,
    ItemKind,
    MockOutcome,
    Procurement,
    Quantity,
    ReorderPolicy,
    SignedQuantity,
    Supplier,
)
from app.inventory.rules import Anomaly, StockStatus

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
            raise ValueError(INVENTORY_ZERO_ADJUST_MESSAGE)
        return value


class CloseCheckRequest(BaseModel):
    counts: dict[str, Quantity] = Field(default_factory=dict)


class CloseRequest(BaseModel):
    """S05 하루 마감. counts에 없는 품목은 미입력. confirmed는 이상 수량을 확인한 품목 id."""

    close_date: date
    counts: dict[str, Quantity] = Field(default_factory=dict)
    adjustments: list[Adjustment] = Field(default_factory=list)
    confirmed: list[str] = Field(default_factory=list)


class InventorySettingsRequest(InventorySettings):
    """요청 본문용 이름. 응답에도 같은 모델이 실려 이름이 같으면 OpenAPI가 -Input/-Output으로 갈라진다."""


class ReorderPolicyRequest(ReorderPolicy):
    """요청 본문용 이름(위와 같은 까닭)."""


class ItemView(ContractModel):
    item: Item
    on_hand: Decimal | None  # None = 미입력
    in_transit: Decimal
    status: StockStatus
    suggested_quantity: Decimal | None  # 부족할 때만. 제작 품목이면 '제작 필요' 수량
    policy: ReorderPolicy | None
    last_counted_at: datetime | None


class InventoryView(ContractModel):
    items: list[ItemView]  # 숨긴 품목 포함(item.archived). 화면이 거른다
    suppliers: list[Supplier]
    settings: InventorySettings
    last_close: Close | None


class CloseCheckView(ContractModel):
    anomalies: list[Anomaly]


class CloseView(ContractModel):
    close: Close
    inventory: InventoryView
