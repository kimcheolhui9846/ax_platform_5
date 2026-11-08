from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from app.inventory.models import (
    AdjustEntry,
    AutoOrderSetting,
    CountEntry,
    Hold,
    HoldReason,
    InventorySettings,
    InventoryState,
    Item,
    ItemKind,
    Order,
    OrderLine,
    OrderOrigin,
    OrderStatus,
    Procurement,
    ReceiptEntry,
    ReorderPolicy,
)
from app.inventory.rules import (
    KST,
    Anomaly,
    AnomalyKind,
    AutoAction,
    StockStatus,
    daily_usage,
    find_anomalies,
    has_unknown_order,
    in_transit,
    is_stale,
    item_status,
    last_counted_at,
    line_amount,
    month_auto_spend,
    on_hand,
    plan_auto_orders,
    suggested_quantity,
)

T1 = datetime(2026, 11, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def count(qty, item="a", at=T1):
    return CountEntry(item_id=item, quantity=D(qty), at=at)


def adjust(delta, item="a"):
    return AdjustEntry(item_id=item, delta=D(delta), reason="사유")


def policy(min_stock="10", target="30", unit="12"):
    return ReorderPolicy(min_stock=D(min_stock), target_stock=D(target), purchase_unit=D(unit), lead_days=3, unit_price=D(1000))


@pytest.mark.parametrize(
    ("ledger", "expected"),
    [
        ([], None),  # 센 적 없음 = 미입력
        ([adjust("3")], None),  # 실사 전 조정은 반영하지 않는다
        ([count("10")], D("10")),
        ([count("10"), adjust("-2.5")], D("7.5")),
        ([count("10"), adjust("-2"), count("4")], D("4")),  # 마지막 실사가 기준
        ([count("10"), count("99", item="b")], D("10")),  # 다른 품목은 무시
    ],
)
def test_on_hand(ledger, expected):
    assert on_hand(ledger, "a") == expected


def receipt(qty, item="a", counted=False):
    return ReceiptEntry(item_id=item, quantity=D(qty), order_id="or_x", already_counted=counted)


@pytest.mark.parametrize(
    ("ledger", "expected"),
    [
        ([count("10"), receipt("5")], D(15)),
        ([count("10"), receipt("5", counted=True)], D(10)),  # 이미 마감에서 셌다: 중복 가산 금지
        ([receipt("5")], None),  # 센 적 없으면 입고만으로 수량을 정하지 않는다
        ([count("10"), receipt("5"), count("12")], D(12)),
    ],
)
def test_on_hand_with_receipts(ledger, expected):
    assert on_hand(ledger, "a") == expected


def order(status, *lines):
    return Order(
        request_id="req-00000001",
        supplier_id="sup_a",
        lines=[OrderLine(item_id=i, quantity=D(q), unit_price=D(100), received=D(r)) for i, q, r in lines],
        total=D(0),
        origin=OrderOrigin.MANUAL,
        status=status,
    )


def test_in_transit_counts_open_orders_remaining_quantity():
    orders = [
        order(OrderStatus.ACCEPTED, ("a", "10", "0"), ("b", "3", "0")),
        order(OrderStatus.PARTIALLY_RECEIVED, ("a", "10", "4")),
        order(OrderStatus.UNKNOWN, ("a", "100", "0")),  # 접수 여부를 모르면 배송 중이 아니다
        order(OrderStatus.REJECTED, ("a", "100", "0")),
        order(OrderStatus.RECEIVED, ("a", "5", "5")),
    ]
    assert in_transit(orders, "a") == D(16)
    assert in_transit(orders, "b") == D(3)
    assert in_transit(orders, "c") == D(0)


def test_last_counted_at():
    assert last_counted_at([], "a") is None
    assert last_counted_at([count("1", at=T1), adjust("1"), count("2", at=T2)], "a") == T2


@pytest.mark.parametrize(
    ("qty", "in_transit", "pol", "expected"),
    [
        (None, D(0), policy(), StockStatus.UNCOUNTED),
        (D(5), D(0), policy(), StockStatus.SHORT),
        (D(5), D(5), policy(), StockStatus.IN_TRANSIT),  # 5+5 = 최소 10이면 부족 아님
        (D(5), D(0), None, StockStatus.OK),  # 기준이 없으면 부족 판정 안 함
        (D(20), D(0), policy(), StockStatus.OK),
    ],
)
def test_item_status(qty, in_transit, pol, expected):
    assert item_status(qty, in_transit, pol) is expected


@pytest.mark.parametrize(
    ("qty", "in_transit", "pol", "expected"),
    [
        (D(5), D(0), policy(), D(36)),  # 목표 30 − 5 = 25 → 12 단위로 올림 = 36
        (D(6), D(0), policy(), D(24)),  # 24 → 그대로 24
        (D("4.5"), D(0), policy(unit="0.5"), D("25.5")),
        (D(20), D(0), policy(), None),  # 부족 아님
        (None, D(0), policy(), None),  # 미입력
        (D(5), D(0), None, None),  # 기준 없음
        (D(2), D(3), policy(), D(36)),  # 2+3 = 5 < 최소 10, 목표 30 − 2 = 28 → 12 단위로 올림 = 36
    ],
)
def test_suggested_quantity(qty, in_transit, pol, expected):
    assert suggested_quantity(qty, in_transit, pol) == expected


def test_find_anomalies_increase_and_drop_in_counts_order():
    ledger = [count("10"), count("10", item="b"), count("10", item="c"), count("0", item="d")]
    counts = {"b": D(4), "a": D(11), "c": D(5), "d": D(0), "new": D(3)}

    found = find_anomalies(ledger, counts, D("0.5"))

    assert found == [
        Anomaly(item_id="b", previous=D(10), counted=D(4), kind=AnomalyKind.DROP),  # 60% 감소 > 50%
        Anomaly(item_id="a", previous=D(10), counted=D(11), kind=AnomalyKind.INCREASE),
    ]  # c는 정확히 50%라 아님, d는 직전 0, new는 센 적 없음


def test_find_anomalies_equal_count_is_not_an_anomaly():
    assert find_anomalies([count("10")], {"a": D(10)}, D("0.5")) == []


def test_find_anomalies_uses_the_adjusted_baseline():
    ledger = [count("10"), adjust("-2.5")]  # 직전 수량 7.5
    assert find_anomalies(ledger, {"a": D("7.5")}, D("0.5")) == []
    assert find_anomalies(ledger, {"a": D(3)}, D("0.5")) == [
        Anomaly(item_id="a", previous=D("7.5"), counted=D(3), kind=AnomalyKind.DROP)  # 4.5/7.5 = 0.6 > 0.5
    ]


NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)


def auto_state(**overrides):
    """구매 품목 a(보유 5, 최소 10·목표 30·단위 12·단가 1000), 자동 주문 켬(1회 5만·월 10만)."""
    item = Item(item_id="a", name="원단", kind=ItemKind.MATERIAL, unit="m", procurement=Procurement.PURCHASE, supplier_id="sup")
    values = {
        "owner_id": "client-aaaa",
        "items": [item],
        "policies": {"a": policy()},
        "ledger": [count("5", at=NOW - timedelta(days=1))],
        "auto_orders": {"a": AutoOrderSetting(enabled=True, consented_at=NOW, per_order_limit=D(50000), monthly_limit=D(100000))},
        "settings": InventorySettings(address="서울시 어딘가 1"),
    }
    return InventoryState(**(values | overrides))


def test_is_stale():
    assert is_stale(None, NOW, 7) is True
    assert is_stale(NOW - timedelta(days=7), NOW, 7) is False
    assert is_stale(NOW - timedelta(days=7, seconds=1), NOW, 7) is True


def test_line_amount_rounds_to_cents_half_up():
    assert line_amount(D("1.5"), D("1234.55")) == D("1851.83")  # 1851.825
    assert line_amount(D("0.33"), D("0.33")) == D("0.11")  # 0.1089
    assert line_amount(D("2.50"), D("1000.00")) == D("2500.00")


def auto_order(status, lines, created=NOW, origin=OrderOrigin.AUTO):
    """lines: (품목, 수량, 단가)."""
    return Order(
        request_id="auto:cl_x:a",
        supplier_id="sup",
        lines=[OrderLine(item_id=i, quantity=D(q), unit_price=D(p)) for i, q, p in lines],
        total=D(0),
        origin=origin,
        status=status,
        created_at=created,
    )


def test_month_auto_spend_counts_only_this_items_auto_orders_this_month_that_may_ship():
    orders = [
        auto_order(OrderStatus.ACCEPTED, [("a", "1", "100")]),
        auto_order(OrderStatus.UNKNOWN, [("a", "1", "20")]),
        auto_order(OrderStatus.RECEIVED, [("a", "1", "3")]),
        auto_order(OrderStatus.PARTIALLY_RECEIVED, [("a", "1.5", "1234.55")]),  # 1851.83
        auto_order(OrderStatus.REJECTED, [("a", "1", "999")]),
        auto_order(OrderStatus.ACCEPTED, [("a", "1", "999")], created=datetime(2026, 10, 31, tzinfo=timezone.utc)),
        auto_order(OrderStatus.ACCEPTED, [("a", "1", "999")], origin=OrderOrigin.MANUAL),
        auto_order(OrderStatus.ACCEPTED, [("b", "1", "999")]),  # 다른 품목
    ]
    assert month_auto_spend(orders, "a", 2026, 11) == D("1974.83")
    assert month_auto_spend(orders, "b", 2026, 11) == D(999)
    assert has_unknown_order(orders, "a") is True
    assert has_unknown_order(orders, "b") is False


def test_month_auto_spend_uses_korean_month():
    early_first = auto_order(OrderStatus.ACCEPTED, [("a", "1", "100")], created=datetime(2026, 10, 31, 16, tzinfo=timezone.utc))
    late_last = auto_order(OrderStatus.ACCEPTED, [("a", "1", "7")], created=datetime(2026, 10, 31, 14, 59, tzinfo=timezone.utc))
    assert early_first.created_at.astimezone(KST).day == 1  # 11-01 01:00 KST
    assert month_auto_spend([early_first, late_last], "a", 2026, 11) == D(100)
    assert month_auto_spend([early_first, late_last], "a", 2026, 10) == D(7)


def decision(state):
    return [(d.item_id, d.action, d.quantity, d.amount, d.reason) for d in plan_auto_orders(state, NOW)]


def test_plan_orders_suggested_quantity_within_limits():
    assert decision(auto_state()) == [("a", AutoAction.ORDER, D(36), D(36000), None)]


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"ledger": [count("5", at=NOW - timedelta(days=8))]}, HoldReason.STALE_COUNT),
        ({"orders": [order(OrderStatus.UNKNOWN, ("a", "1", "0"))]}, HoldReason.UNKNOWN),
        (
            {"auto_orders": {"a": AutoOrderSetting(enabled=True, consented_at=NOW, per_order_limit=D(30000), monthly_limit=D(100000))}},
            HoldReason.LIMIT_EXCEEDED,
        ),
        (
            {"auto_orders": {"a": AutoOrderSetting(enabled=True, consented_at=NOW, per_order_limit=D(50000), monthly_limit=D(35999))}},
            HoldReason.LIMIT_EXCEEDED,
        ),
    ],
)
def test_plan_holds(overrides, reason):
    assert decision(auto_state(**overrides)) == [("a", AutoAction.HOLD, D(36), D(36000), reason)]


def test_plan_skips_items_not_short_disabled_unconsented_or_make():
    assert decision(auto_state(ledger=[count("40", at=NOW)])) == []
    off = AutoOrderSetting(enabled=False, consented_at=NOW, per_order_limit=D(50000), monthly_limit=D(100000))
    assert decision(auto_state(auto_orders={"a": off})) == []
    unconsented = AutoOrderSetting(enabled=True, per_order_limit=D(50000), monthly_limit=D(100000))
    assert decision(auto_state(auto_orders={"a": unconsented})) == []
    made = Item(item_id="a", name="에코백", kind=ItemKind.FINISHED, unit="개", procurement=Procurement.MAKE)
    assert decision(auto_state(items=[made])) == []


def test_plan_monthly_limit_is_per_item():
    second = Item(item_id="b", name="실", kind=ItemKind.MATERIAL, unit="m", procurement=Procurement.PURCHASE, supplier_id="sup")
    setting = AutoOrderSetting(enabled=True, consented_at=NOW, per_order_limit=D(50000), monthly_limit=D(50000))
    state = auto_state(
        items=[auto_state().items[0], second],
        policies={"a": policy(), "b": policy()},
        ledger=[count("5", at=NOW), count("5", item="b", at=NOW)],
        auto_orders={"a": setting, "b": setting},
        orders=[auto_order(OrderStatus.RECEIVED, [("a", "20", "1000")])],  # a만 이번 달 2만 썼다(다 받아 배송 중은 아니다)
    )
    assert [(d.item_id, d.action, d.reason) for d in plan_auto_orders(state, NOW)] == [
        ("a", AutoAction.HOLD, HoldReason.LIMIT_EXCEEDED),  # 2만 + 3.6만 > 5만
        ("b", AutoAction.ORDER, None),  # b의 한도는 a의 주문과 상관없다
    ]


def test_plan_month_starts_in_korean_time():
    now = datetime(2026, 10, 31, 16, tzinfo=timezone.utc)  # 11-01 01:00 KST
    limited = AutoOrderSetting(enabled=True, consented_at=now, per_order_limit=D(50000), monthly_limit=D(50000))
    state = auto_state(
        ledger=[count("5", at=now)],
        auto_orders={"a": limited},
        orders=[
            auto_order(OrderStatus.RECEIVED, [("a", "10", "1000")], created=now - timedelta(minutes=30)),  # 11-01 00:30 KST
            auto_order(OrderStatus.RECEIVED, [("a", "20", "1000")], created=now - timedelta(hours=2)),  # 10-31 23:00 KST
        ],
    )
    # 11월(KST)은 1만만 썼다: 1만 + 3.6만 ≤ 5만. UTC로 보면 3만 + 3.6만이라 보류됐을 것이다
    assert [d.action for d in plan_auto_orders(state, now)] == [AutoAction.ORDER]


def test_plan_amount_is_rounded_to_cents():
    fractional = ReorderPolicy(min_stock=D(10), target_stock=D(30), purchase_unit=D("1.5"), lead_days=3, unit_price=D("1234.55"))
    [(_, action, quantity, amount, _)] = decision(auto_state(policies={"a": fractional}))
    assert (action, quantity, amount) == (AutoAction.ORDER, D("25.5"), D("31481.03"))  # 31481.025


def test_plan_holds_when_address_is_missing():
    state = auto_state(settings=InventorySettings())
    assert decision(state) == [("a", AutoAction.HOLD, D(36), D(36000), HoldReason.ADDRESS_MISSING)]


@pytest.mark.parametrize("reason", [HoldReason.PRICE_CHANGED, HoldReason.OUT_OF_STOCK])
def test_plan_pauses_item_with_open_supplier_hold(reason):
    open_hold = Hold(item_id="a", reason=reason, order_id="or_x")
    assert decision(auto_state(holds=[open_hold])) == []
    resolved = open_hold.model_copy(update={"resolved": True})
    assert decision(auto_state(holds=[resolved]))[0][1] is AutoAction.ORDER
    other_item = open_hold.model_copy(update={"item_id": "b"})
    assert decision(auto_state(holds=[other_item]))[0][1] is AutoAction.ORDER


def test_plan_other_open_holds_do_not_pause():
    stale = Hold(item_id="a", reason=HoldReason.STALE_COUNT)
    assert decision(auto_state(holds=[stale]))[0][1] is AutoAction.ORDER


def test_daily_usage():
    t0 = datetime(2026, 11, 1, tzinfo=timezone.utc)
    ledger = [
        count("20", at=t0),
        count("14", at=t0 + timedelta(days=2)),  # 6 소진
        receipt("10"),  # 24
        count("18", at=t0 + timedelta(days=4)),  # 6 소진
        count("19", at=t0 + timedelta(days=5)),  # 늘었으면 소진 아님
    ]
    assert daily_usage(ledger, "a") == D("2.40")  # 12 / 5일
    assert daily_usage([count("5", at=t0)], "a") is None
    assert daily_usage([count("5", at=t0), count("4", at=t0)], "a") is None
