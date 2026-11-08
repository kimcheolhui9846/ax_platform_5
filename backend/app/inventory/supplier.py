"""거래처 계약. 실제 쇼핑몰·결제는 붙이지 않고(비용 0) Mock이 기본이다. 실제 거래처는 이 계약만 구현한다.

계약:
- place는 주문을 넣고, lookup은 같은 request_id의 상태를 다시 묻는다(다시 주문하지 않는다).
- 통신 오류·시간 초과는 예외로 던지지 말고 ReplyStatus.UNKNOWN으로 돌려준다. 주문이 실제로 들어갔을 수 있어서다.
  (그래도 예외가 나면 service가 place는 접수 불명으로, lookup은 그대로 접수 불명으로 둔다.)
- 응답은 SupplierReply가 검증한다: 거절에만 사유가 있고, 단가는 저장 모델과 같은 금액 형식(0 이상, 둘째 자리까지)이다.
"""
from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from app.inventory.models import MockOutcome, Money, OrderLine, RejectReason, Supplier

PRICE_CHANGE_RATE = Decimal("1.1")  # Mock 가격 변동: 단가 +10%
CENT = Decimal("0.01")


class ReplyStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class SupplierReply(BaseModel):
    """값은 OrderStatus와 같다(service가 OrderStatus(reply.status)로 옮긴다)."""

    status: ReplyStatus
    reason: RejectReason | None = None
    current_prices: dict[str, Money] = Field(default_factory=dict)
    supplier_ref: str | None = None

    @model_validator(mode="after")
    def _reason_only_when_rejected(self) -> "SupplierReply":
        if (self.status is ReplyStatus.REJECTED) != (self.reason is not None):
            raise ValueError("거절 응답에만 사유가 있어야 합니다.")
        return self


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
