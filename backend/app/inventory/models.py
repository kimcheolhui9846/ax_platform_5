"""재고 묶음(owner마다 하나)의 저장 모델. 수량은 저장하지 않고 원장에서 계산한다(rules.py).

원장(ledger)은 추가만 하고 고치지 않는다. 같은 품목의 순서는 목록 순서다(시각이 같아도 흔들리지 않는다).
새 필드는 기본값을 둬서 저장된 옛 문서도 그대로 읽히게 한다.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import AfterValidator, Field

from app.core.contract import ContractModel
from app.core.results import utcnow


def _plain(value: Decimal) -> Decimal:
    """'1e3'처럼 지수로 들어온 값도 '1000'으로 나가게 한다(값은 그대로)."""
    return Decimal(format(value, "f"))


Quantity = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2), AfterValidator(_plain)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2), AfterValidator(_plain)]
SignedQuantity = Annotated[Decimal, Field(max_digits=12, decimal_places=2), AfterValidator(_plain)]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2), AfterValidator(_plain)]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class ItemKind(StrEnum):
    FINISHED = "finished"  # 완제품
    MATERIAL = "material"  # 재료
    PACKAGING = "packaging"  # 포장재


class Procurement(StrEnum):
    PURCHASE = "purchase"  # 거래처에서 산다
    MAKE = "make"  # 직접 만든다(부족하면 주문 대신 제작 알림)


class MockOutcome(StrEnum):
    """모의 거래처가 낼 결과(PR #41의 SupplierProvider Mock이 쓴다)."""

    ACCEPT = "accept"
    PRICE_CHANGED = "price_changed"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN_THEN_ACCEPT = "unknown_then_accept"


class Item(ContractModel):
    item_id: str = Field(default_factory=lambda: new_id("it"))
    name: str = Field(min_length=1)
    option: str | None = None
    kind: ItemKind
    unit: str = Field(min_length=1)
    procurement: Procurement
    supplier_id: str | None = None  # 구매 품목만. 제작 품목은 늘 None
    archived: bool = False  # 지우지 않고 숨긴다(원장·주문 보존)


class Supplier(ContractModel):
    supplier_id: str = Field(default_factory=lambda: new_id("sup"))
    name: str = Field(min_length=1)
    kind: Literal["mock"] = "mock"
    mock_outcome: MockOutcome = MockOutcome.ACCEPT


class ReorderPolicy(ContractModel):
    min_stock: Quantity
    target_stock: Quantity
    purchase_unit: PositiveQuantity
    lead_days: int = Field(ge=0, le=365)
    unit_price: Money


class InventorySettings(ContractModel):
    address: str = Field(default="", max_length=200)
    anomaly_drop_ratio: Decimal = Field(default=Decimal("0.5"), gt=0, le=1, decimal_places=2)
    stale_days: int = Field(default=7, ge=1, le=90)


class CountEntry(ContractModel):
    """실사: 이 시점의 실제 수량(하루 마감, 일괄 등록의 현재 수량)."""

    type: Literal["count"] = "count"
    entry_id: str = Field(default_factory=lambda: new_id("le"))
    item_id: str
    quantity: Quantity
    at: datetime = Field(default_factory=utcnow)
    close_id: str | None = None


class AdjustEntry(ContractModel):
    """조정: 마지막 실사에 더하거나 뺀다. 사유가 필수다."""

    type: Literal["adjust"] = "adjust"
    entry_id: str = Field(default_factory=lambda: new_id("le"))
    item_id: str
    delta: SignedQuantity
    reason: str = Field(min_length=1)
    at: datetime = Field(default_factory=utcnow)
    close_id: str | None = None


LedgerEntry = Annotated[CountEntry | AdjustEntry, Field(discriminator="type")]


class Close(ContractModel):
    close_id: str = Field(default_factory=lambda: new_id("cl"))
    close_date: date
    counts: dict[str, Quantity]  # 적지 않은 품목은 미입력(0이 아니다)
    at: datetime = Field(default_factory=utcnow)


class InventoryState(ContractModel):
    owner_id: str
    items: list[Item] = Field(default_factory=list)
    suppliers: list[Supplier] = Field(default_factory=list)
    policies: dict[str, ReorderPolicy] = Field(default_factory=dict)  # 품목 id → 기준
    ledger: list[LedgerEntry] = Field(default_factory=list)
    closes: list[Close] = Field(default_factory=list)
    settings: InventorySettings = Field(default_factory=InventorySettings)
    updated_at: datetime = Field(default_factory=utcnow)
