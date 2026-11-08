"""재고 계산. 모두 값을 받아 값을 돌려주는 순수 함수다. 상태를 바꾸지 않는다."""
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.core.contract import ContractModel
from app.inventory.models import (
    AdjustEntry,
    CountEntry,
    Hold,
    HoldReason,
    InventoryState,
    LedgerEntry,
    Order,
    OrderOrigin,
    OrderStatus,
    Procurement,
    ReceiptEntry,
    ReorderPolicy,
)


KST = timezone(timedelta(hours=9))  # 사용자는 한국에 있다. 서머타임이 없어 고정 시차로 충분하다(tzdata 불필요)
CENT = Decimal("0.01")


def line_amount(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """수량 × 단가를 소수 둘째 자리까지 반올림한다(ROUND_HALF_UP). 금액은 둘째 자리까지 저장한다."""
    return (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP)


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


def has_unknown_order(orders: Sequence[Order], item_id: str) -> bool:
    return any(o.status is OrderStatus.UNKNOWN and any(l.item_id == item_id for l in o.lines) for o in orders)


_SPENT_STATUSES = (OrderStatus.ACCEPTED, OrderStatus.UNKNOWN, OrderStatus.PARTIALLY_RECEIVED, OrderStatus.RECEIVED)


def month_auto_spend(orders: Sequence[Order], item_id: str, year: int, month: int) -> Decimal:
    """그 품목의 자동 주문 중 그 달(한국 시각)에 만들었고 나갔거나 나갔을 수 있는 주문(거절 제외)의 금액 합."""
    return sum(
        (
            line_amount(line.quantity, line.unit_price)
            for o in orders
            if o.origin is OrderOrigin.AUTO
            and o.status in _SPENT_STATUSES
            and (o.created_at.astimezone(KST).year, o.created_at.astimezone(KST).month) == (year, month)
            for line in o.lines
            if line.item_id == item_id
        ),
        Decimal(0),
    )


_PAUSING_HOLDS = (HoldReason.PRICE_CHANGED, HoldReason.OUT_OF_STOCK)


def is_paused(holds: Sequence[Hold], item_id: str) -> bool:
    """거래처가 거절한 보류(가격 변동·품절)가 풀리지 않았으면 사용자가 해결할 때까지 자동 주문을 멈춘다."""
    return any(h.item_id == item_id and h.reason in _PAUSING_HOLDS and not h.resolved for h in holds)


def is_stale(last_counted: datetime | None, now: datetime, stale_days: int) -> bool:
    return last_counted is None or now - last_counted > timedelta(days=stale_days)


class AutoAction(StrEnum):
    ORDER = "order"
    HOLD = "hold"


class AutoDecision(ContractModel):
    item_id: str
    action: AutoAction
    quantity: Decimal | None
    amount: Decimal | None
    reason: HoldReason | None


def plan_auto_orders(state: InventoryState, now: datetime) -> list[AutoDecision]:
    """자동 주문 대상 품목마다 주문할지 보류할지 정한다(품목 순서). AI는 관여하지 않는다.
    한도는 품목마다다: 1회 한도와 그 품목의 이번 달(한국 시각) 자동 주문 합계를 본다."""
    decisions: list[AutoDecision] = []
    local = now.astimezone(KST)
    for item in state.items:
        setting = state.auto_orders.get(item.item_id)
        policy = state.policies.get(item.item_id)
        if (
            setting is None
            or not setting.enabled
            or setting.consented_at is None
            or item.archived
            or item.procurement is not Procurement.PURCHASE
            or item.supplier_id is None
            or policy is None
            or is_paused(state.holds, item.item_id)
        ):
            continue
        quantity = suggested_quantity(on_hand(state.ledger, item.item_id), in_transit(state.orders, item.item_id), policy)
        if quantity is None:
            continue
        amount = line_amount(quantity, policy.unit_price)
        spent = month_auto_spend(state.orders, item.item_id, local.year, local.month)

        def hold(reason: HoldReason) -> AutoDecision:
            return AutoDecision(item_id=item.item_id, action=AutoAction.HOLD, quantity=quantity, amount=amount, reason=reason)

        if not state.settings.address:
            decisions.append(hold(HoldReason.ADDRESS_MISSING))
        elif is_stale(last_counted_at(state.ledger, item.item_id), now, state.settings.stale_days):
            decisions.append(hold(HoldReason.STALE_COUNT))
        elif has_unknown_order(state.orders, item.item_id):
            decisions.append(hold(HoldReason.UNKNOWN))
        elif amount > setting.per_order_limit or spent + amount > setting.monthly_limit:
            decisions.append(hold(HoldReason.LIMIT_EXCEEDED))
        else:
            decisions.append(AutoDecision(item_id=item.item_id, action=AutoAction.ORDER, quantity=quantity, amount=amount, reason=None))
    return decisions


def daily_usage(ledger: Sequence[LedgerEntry], item_id: str) -> Decimal | None:
    """실사 사이에 줄어든 양의 합 ÷ 첫·마지막 실사 사이 날 수(소수 둘째 자리). 실사가 둘 미만이거나 기간이 0이면 None."""
    counts = [(i, e) for i, e in enumerate(ledger) if isinstance(e, CountEntry) and e.item_id == item_id]
    if len(counts) < 2:
        return None
    days = Decimal((counts[-1][1].at - counts[0][1].at).total_seconds()) / Decimal(86400)
    if days <= 0:
        return None
    used = Decimal(0)
    for index, entry in counts[1:]:
        before = on_hand(ledger[:index], item_id)
        if before is not None and before > entry.quantity:
            used += before - entry.quantity
    return (used / days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
