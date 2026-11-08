"""거래처 계약. 실제 쇼핑몰·결제는 붙이지 않고(비용 0) Mock이 기본이다. 실제 거래처는 이 계약만 구현한다.

계약:
- place는 주문을 넣고, lookup은 같은 request_id의 상태를 다시 묻는다(다시 주문하지 않는다).
- 통신 오류·시간 초과는 예외로 던지지 말고 ReplyStatus.UNKNOWN으로 돌려준다. 주문이 실제로 들어갔을 수 있어서다.
"""
from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from app.inventory.models import MockOutcome, OrderLine, RejectReason, Supplier

PRICE_CHANGE_RATE = Decimal("1.1")  # Mock 가격 변동: 단가 +10%
CENT = Decimal("0.01")


class ReplyStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class SupplierReply(BaseModel):
    status: ReplyStatus
    reason: RejectReason | None = None
    current_prices: dict[str, Decimal] = Field(default_factory=dict)
    supplier_ref: str | None = None


class SupplierProvider(Protocol):
    def place(self, supplier: Supplier, request_id: str, lines: Sequence[OrderLine], address: str) -> SupplierReply: ...

    def lookup(self, supplier: Supplier, request_id: str, lines: Sequence[OrderLine]) -> SupplierReply: ...


class MockSupplier:
    """저장 없이 늘 같은 답을 낸다. 결과는 거래처의 mock_outcome이 정한다."""

    def place(self, supplier: Supplier, request_id: str, lines: Sequence[OrderLine], address: str) -> SupplierReply:
        if supplier.mock_outcome is MockOutcome.UNKNOWN_THEN_ACCEPT:
            return SupplierReply(status=ReplyStatus.UNKNOWN)
        return self._settled(supplier, request_id, lines)

    def lookup(self, supplier: Supplier, request_id: str, lines: Sequence[OrderLine]) -> SupplierReply:
        return self._settled(supplier, request_id, lines)

    @staticmethod
    def _settled(supplier: Supplier, request_id: str, lines: Sequence[OrderLine]) -> SupplierReply:
        if supplier.mock_outcome is MockOutcome.PRICE_CHANGED:
            prices = {line.item_id: (line.unit_price * PRICE_CHANGE_RATE).quantize(CENT) for line in lines}
            return SupplierReply(status=ReplyStatus.REJECTED, reason=RejectReason.PRICE_CHANGED, current_prices=prices)
        if supplier.mock_outcome is MockOutcome.OUT_OF_STOCK:
            return SupplierReply(status=ReplyStatus.REJECTED, reason=RejectReason.OUT_OF_STOCK)
        return SupplierReply(status=ReplyStatus.ACCEPTED, supplier_ref=f"mock-{request_id}")


def get_supplier_provider(name: str) -> SupplierProvider:
    if name == "mock":
        return MockSupplier()
    raise ValueError(f"없는 거래처 제공자입니다: {name}")
