"""재고 계산. 모두 값을 받아 값을 돌려주는 순수 함수다. 상태를 바꾸지 않는다."""
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum

from app.core.contract import ContractModel
from app.inventory.models import AdjustEntry, CountEntry, LedgerEntry, Order, OrderStatus, ReceiptEntry, ReorderPolicy


class StockStatus(StrEnum):
    UNCOUNTED = "uncounted"  # 미입력(센 적 없음)
    SHORT = "short"  # 보유 + 배송 중 < 최소
    IN_TRANSIT = "in_transit"
    OK = "ok"


class AnomalyKind(StrEnum):
    INCREASE = "increase"  # 입고 없이 늘었다
    DROP = "drop"  # 기준보다 많이 줄었다


class Anomaly(ContractModel):
    item_id: str
    previous: Decimal
    counted: Decimal
    kind: AnomalyKind


def on_hand(ledger: Sequence[LedgerEntry], item_id: str) -> Decimal | None:
    """마지막 실사 + 그 뒤의 조정·입고. 실사가 없으면 None(미입력). 실사 전 조정·입고는 반영하지 않는다.
    already_counted 입고는 이미 마감에서 센 물건이라 더하지 않는다(중복 가산 방지)."""
    total: Decimal | None = None
    for entry in ledger:
        if entry.item_id != item_id:
            continue
        if isinstance(entry, CountEntry):
            total = entry.quantity
        elif total is None:
            continue
        elif isinstance(entry, AdjustEntry):
            total += entry.delta
        elif isinstance(entry, ReceiptEntry) and not entry.already_counted:
            total += entry.quantity
    return total


OPEN_STATUSES = (OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_RECEIVED)


def in_transit(orders: Sequence[Order], item_id: str) -> Decimal:
    """접수됐고 아직 다 받지 않은 주문의 (주문 − 받은) 수량 합. 접수 불명은 넣지 않는다."""
    return sum(
        (line.quantity - line.received for o in orders if o.status in OPEN_STATUSES for line in o.lines if line.item_id == item_id),
        Decimal(0),
    )


def last_counted_at(ledger: Sequence[LedgerEntry], item_id: str) -> datetime | None:
    counted = [e.at for e in ledger if isinstance(e, CountEntry) and e.item_id == item_id]
    return counted[-1] if counted else None


def item_status(on_hand_qty: Decimal | None, in_transit: Decimal, policy: ReorderPolicy | None) -> StockStatus:
    if on_hand_qty is None:
        return StockStatus.UNCOUNTED
    if policy is not None and on_hand_qty + in_transit < policy.min_stock:
        return StockStatus.SHORT
    if in_transit > 0:
        return StockStatus.IN_TRANSIT
    return StockStatus.OK


def suggested_quantity(on_hand_qty: Decimal | None, in_transit: Decimal, policy: ReorderPolicy | None) -> Decimal | None:
    """부족할 때만 (목표 − 보유 − 배송 중)을 구매 단위로 올린 값. 아니면 None."""
    if policy is None or item_status(on_hand_qty, in_transit, policy) is not StockStatus.SHORT:
        return None
    gap = policy.target_stock - on_hand_qty - in_transit
    if gap <= 0:
        return None
    units = (gap / policy.purchase_unit).to_integral_value(rounding=ROUND_CEILING)
    return units * policy.purchase_unit


def find_anomalies(ledger: Sequence[LedgerEntry], counts: Mapping[str, Decimal], drop_ratio: Decimal) -> list[Anomaly]:
    """센 수량이 직전 보유보다 늘었거나, 직전 대비 drop_ratio보다 많이 줄었으면 확인이 필요하다(counts 순서)."""
    found: list[Anomaly] = []
    for item_id, counted in counts.items():
        previous = on_hand(ledger, item_id)
        if previous is None:
            continue
        if counted > previous:
            found.append(Anomaly(item_id=item_id, previous=previous, counted=counted, kind=AnomalyKind.INCREASE))
        elif previous > 0 and (previous - counted) / previous > drop_ratio:
            found.append(Anomaly(item_id=item_id, previous=previous, counted=counted, kind=AnomalyKind.DROP))
    return found
