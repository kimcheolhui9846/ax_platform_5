from datetime import datetime, timezone
from decimal import Decimal as D

import pytest

from app.inventory.models import (
    AdjustEntry,
    CountEntry,
    Order,
    OrderLine,
    OrderOrigin,
    OrderStatus,
    ReceiptEntry,
    ReorderPolicy,
)
from app.inventory.rules import (
    Anomaly,
    AnomalyKind,
    StockStatus,
    find_anomalies,
    in_transit,
    item_status,
    last_counted_at,
    on_hand,
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
