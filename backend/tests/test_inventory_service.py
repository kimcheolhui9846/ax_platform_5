from datetime import date
from decimal import Decimal as D

import pytest

from app.core.messages import (
    INVENTORY_CONSENT_REQUIRED_MESSAGE,
    INVENTORY_ADJUST_UNCOUNTED_MESSAGE,
    INVENTORY_EMPTY_CLOSE_MESSAGE,
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_NEGATIVE_STOCK_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    INVENTORY_ADDRESS_REQUIRED_MESSAGE,
    INVENTORY_DUPLICATE_LINE_MESSAGE,
    INVENTORY_HOLD_NOT_FOUND_MESSAGE,
    INVENTORY_MIXED_SUPPLIER_MESSAGE,
    INVENTORY_NOT_ORDERABLE_MESSAGE,
    INVENTORY_ORDER_NOT_FOUND_MESSAGE,
    INVENTORY_ORDER_NOT_RECEIVABLE_MESSAGE,
    INVENTORY_OVER_RECEIPT_MESSAGE,
    INVENTORY_POLICY_REQUIRED_MESSAGE,
    INVENTORY_RECEIPT_ITEM_MESSAGE,
    INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE,
    unconfirmed_anomaly_message,
    duplicate_item_message,
)
from app.inventory import service
from app.providers.base import ProviderError
from app.providers.mock import MockProvider
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import (
    AdjustEntry,
    CountEntry,
    HoldReason,
    InventorySettings,
    InventoryState,
    MockOutcome,
    OrderOrigin,
    OrderStatus,
    ReceiptEntry,
    RejectReason,
    ReorderPolicy,
)
from app.inventory.rules import AnomalyKind, in_transit, on_hand
from app.inventory.supplier import MockSupplier
from app.schemas.inventory import AutoOrderRequest, Adjustment, OrderRequest, ReceiptRequest, CloseRequest, ItemDraft, ItemPatch, SupplierDraft, SupplierPatch


def draft(name="에코백", **overrides) -> ItemDraft:
    values = {"name": name, "kind": "finished", "unit": "개", "procurement": "make"}
    return ItemDraft(**(values | overrides))


def fresh() -> InventoryState:
    return InventoryState(owner_id="client-aaaa")


def test_add_items_records_initial_quantity_as_count():
    state = fresh()
    items = service.add_items(state, [draft(quantity=D(5)), draft("원단", kind="material", unit="m")])

    assert [i.name for i in state.items] == ["에코백", "원단"]
    assert on_hand(state.ledger, items[0].item_id) == D(5)
    assert on_hand(state.ledger, items[1].item_id) is None  # 수량을 안 적으면 미입력
    assert isinstance(state.ledger[0], CountEntry)


def test_add_items_strips_names():
    state = fresh()
    service.add_items(state, [draft("  에코백  ", option=" 검정 ")])
    assert (state.items[0].name, state.items[0].option) == ("에코백", "검정")


def test_add_items_rejects_duplicates_in_batch_and_existing():
    state = fresh()
    service.add_items(state, [draft(option="검정")])
    with pytest.raises(InventoryError, match=duplicate_item_message("에코백")):
        service.add_items(state, [draft(option="검정")])
    with pytest.raises(InventoryError):
        service.add_items(state, [draft("원단"), draft("원단")])
    service.add_items(state, [draft(option="흰색")])  # 옵션이 다르면 다른 품목
    assert len(state.items) == 2


def test_add_items_checks_supplier_and_drops_it_for_make():
    state = fresh()
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_SUPPLIER_MESSAGE):
        service.add_items(state, [draft(procurement="purchase", supplier_id="sup_none")])
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회"))
    items = service.add_items(
        state,
        [draft("원단", procurement="purchase", supplier_id=supplier.supplier_id), draft("에코백", supplier_id=supplier.supplier_id)],
    )
    assert items[0].supplier_id == supplier.supplier_id
    assert items[1].supplier_id is None  # 제작 품목에는 거래처가 없다


def test_update_item_patches_only_given_fields_and_clears_option():
    state = fresh()
    [item] = service.add_items(state, [draft(option="검정")])

    service.update_item(state, item.item_id, ItemPatch(name="큰 에코백"))
    assert (state.items[0].name, state.items[0].option) == ("큰 에코백", "검정")

    service.update_item(state, item.item_id, ItemPatch(option=None))
    assert state.items[0].option is None

    service.update_item(state, item.item_id, ItemPatch(archived=True))
    assert state.items[0].archived is True


def test_update_item_locks_unit_once_ledger_has_entries():
    state = fresh()
    [counted, empty] = service.add_items(state, [draft(quantity=D(1)), draft("원단", unit="m")])

    with pytest.raises(InventoryError, match=INVENTORY_UNIT_LOCKED_MESSAGE):
        service.update_item(state, counted.item_id, ItemPatch(unit="묶음"))
    service.update_item(state, counted.item_id, ItemPatch(unit="개"))  # 같은 단위는 괜찮다
    service.update_item(state, empty.item_id, ItemPatch(unit="cm"))
    assert state.items[1].unit == "cm"


def test_update_item_unknown_id_is_not_found():
    with pytest.raises(InventoryNotFound, match=INVENTORY_ITEM_NOT_FOUND_MESSAGE):
        service.update_item(fresh(), "it_none", ItemPatch(name="x"))


def test_update_item_rejects_becoming_a_duplicate():
    state = fresh()
    [_, other] = service.add_items(state, [draft(), draft("원단")])
    with pytest.raises(InventoryError):
        service.update_item(state, other.item_id, ItemPatch(name="에코백"))


def test_update_item_unknown_supplier_is_rejected():
    state = fresh()
    [item] = service.add_items(state, [draft(procurement="purchase")])
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_SUPPLIER_MESSAGE):
        service.update_item(state, item.item_id, ItemPatch(supplier_id="sup_none"))


def test_update_item_switching_to_make_clears_supplier():
    state = fresh()
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회"))
    [item] = service.add_items(state, [draft(procurement="purchase", supplier_id=supplier.supplier_id)])
    service.update_item(state, item.item_id, ItemPatch(procurement="make"))
    assert state.items[0].supplier_id is None


def test_update_item_unarchiving_into_a_duplicate_is_rejected():
    state = fresh()
    [old] = service.add_items(state, [draft()])
    service.update_item(state, old.item_id, ItemPatch(archived=True))
    service.add_items(state, [draft()])  # 같은 이름·옵션이 숨김 뒤에 다시 등록됨
    with pytest.raises(InventoryError):
        service.update_item(state, old.item_id, ItemPatch(archived=False))


def test_failed_update_item_leaves_state_untouched():
    state = fresh()
    [_, other] = service.add_items(state, [draft(quantity=D(1)), draft("원단", unit="m")])
    before = state.model_copy(deep=True)
    for item_id, patch in (
        (other.item_id, ItemPatch(name="에코백")),  # 중복
        (other.item_id, ItemPatch(supplier_id="sup_none", procurement="purchase")),  # 없는 거래처
        (state.items[0].item_id, ItemPatch(unit="묶음")),  # 단위 잠김
    ):
        with pytest.raises(InventoryError):
            service.update_item(state, item_id, patch)
    assert state == before


def test_suppliers_add_and_update():
    state = fresh()
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회"))
    service.update_supplier(state, supplier.supplier_id, SupplierPatch(mock_outcome=MockOutcome.OUT_OF_STOCK))
    assert state.suppliers[0].mock_outcome is MockOutcome.OUT_OF_STOCK
    assert state.suppliers[0].name == "원단상회"
    with pytest.raises(InventoryNotFound, match=INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE):
        service.update_supplier(state, "sup_none", SupplierPatch(name="x"))


def test_set_policy_requires_target_at_least_min():
    state = fresh()
    [item] = service.add_items(state, [draft()])
    ok = ReorderPolicy(min_stock=D(5), target_stock=D(5), purchase_unit=D(1), lead_days=2, unit_price=D(0))
    service.set_policy(state, item.item_id, ok)
    assert state.policies[item.item_id] == ok

    bad = ok.model_copy(update={"target_stock": D(4)})
    with pytest.raises(InventoryError, match=INVENTORY_TARGET_BELOW_MIN_MESSAGE):
        service.set_policy(state, item.item_id, bad)
    with pytest.raises(InventoryNotFound):
        service.set_policy(state, "it_none", ok)


def test_set_settings_replaces_settings():
    state = fresh()
    service.set_settings(state, InventorySettings(address="서울시 어딘가", stale_days=3))
    assert state.settings.address == "서울시 어딘가"
    assert state.settings.stale_days == 3


DAY = date(2026, 11, 8)


def stocked(*quantities):
    state = fresh()
    items = service.add_items(state, [draft(f"품목{i}", quantity=q) for i, q in enumerate(quantities)])
    return state, [i.item_id for i in items]


def test_record_close_appends_counts_then_adjustments_and_close():
    state, [a, b] = stocked(D(10), D(10))
    close = service.record_close(
        state,
        CloseRequest(close_date=DAY, counts={a: D(8)}, adjustments=[Adjustment(item_id=a, delta=D(-1), reason="파손")]),
    )

    assert state.closes == [close]
    assert close.counts == {a: D(8)}  # b는 미입력(0이 아니다)
    assert on_hand(state.ledger, a) == D(7)
    assert on_hand(state.ledger, b) == D(10)
    assert [type(e) for e in state.ledger[-2:]] == [CountEntry, AdjustEntry]
    assert all(e.close_id == close.close_id for e in state.ledger[-2:])


def test_check_close_lists_anomalies_without_changing_state():
    state, [a, b] = stocked(D(10), D(10))
    before = state.model_copy(deep=True)

    found = service.check_close(state, {a: D(12), b: D(9)})

    assert [(x.item_id, x.kind) for x in found] == [(a, AnomalyKind.INCREASE)]
    assert state == before


def test_record_close_requires_confirming_every_anomaly():
    state, [a, b] = stocked(D(10), D(10))
    counts = {a: D(12), b: D(1)}
    with pytest.raises(InventoryError, match=unconfirmed_anomaly_message(["품목1"])):  # 품목0(a)은 확인했다
        service.record_close(state, CloseRequest(close_date=DAY, counts=counts, confirmed=[a]))
    assert state.closes == []  # 실패하면 아무것도 남기지 않는다(service는 검사를 모두 끝낸 뒤 고친다)

    service.record_close(state, CloseRequest(close_date=DAY, counts=counts, confirmed=[a, b]))
    assert on_hand(state.ledger, b) == D(1)


def test_same_day_close_again_last_count_wins():
    state, [a] = stocked(D(10))
    service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(9)}))
    service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(8)}))
    assert on_hand(state.ledger, a) == D(8)
    assert len(state.closes) == 2


@pytest.mark.parametrize(
    ("request_kwargs", "message"),
    [
        ({}, INVENTORY_EMPTY_CLOSE_MESSAGE),
        ({"counts": {"it_none": D(1)}}, INVENTORY_UNKNOWN_ITEM_MESSAGE),
        ({"adjustments": [{"item_id": "NEW", "delta": "1", "reason": "r"}]}, INVENTORY_ADJUST_UNCOUNTED_MESSAGE),
        ({"adjustments": [{"item_id": "A", "delta": "-11", "reason": "r"}]}, INVENTORY_NEGATIVE_STOCK_MESSAGE),
    ],
)
def test_record_close_rejections_leave_state_untouched(request_kwargs, message):
    state, [a] = stocked(D(10))
    [new] = service.add_items(state, [draft("새 품목")])
    for adj in request_kwargs.get("adjustments", []):
        adj["item_id"] = {"A": a, "NEW": new.item_id}[adj["item_id"]]
    before = state.model_copy(deep=True)

    with pytest.raises(InventoryError, match=message):
        service.record_close(state, CloseRequest(close_date=DAY, **request_kwargs))
    assert state == before


def test_archived_items_cannot_be_closed():
    state, [a] = stocked(D(10))
    service.update_item(state, a, ItemPatch(archived=True))
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_ITEM_MESSAGE):
        service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(1)}))


def test_adjust_counted_in_same_close_is_allowed():
    state = fresh()
    [item] = service.add_items(state, [draft()])
    service.record_close(
        state,
        CloseRequest(
            close_date=DAY,
            counts={item.item_id: D(3)},
            adjustments=[Adjustment(item_id=item.item_id, delta=D(2), reason="찾음")],
        ),
    )
    assert on_hand(state.ledger, item.item_id) == D(5)


def test_adjustment_delta_cannot_be_zero():
    with pytest.raises(ValueError):
        Adjustment(item_id="it_x", delta=D(0), reason="r")


def test_two_adjustments_to_one_item_sum():
    state, [a] = stocked(D(10))
    service.record_close(
        state,
        CloseRequest(
            close_date=DAY,
            adjustments=[
                Adjustment(item_id=a, delta=D(-2), reason="파손"),
                Adjustment(item_id=a, delta=D("0.5"), reason="찾음"),
            ],
        ),
    )
    assert on_hand(state.ledger, a) == D("8.5")


def test_adjust_item_counted_in_an_earlier_close():
    state, [a, b] = stocked(D(10), D(10))
    service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(10)}))
    service.record_close(
        state,
        CloseRequest(close_date=DAY, counts={b: D(10)}, adjustments=[Adjustment(item_id=a, delta=D(-1), reason="파손")]),
    )
    assert on_hand(state.ledger, a) == D(9)


def test_unknown_id_only_in_adjustments_is_rejected():
    state, _ = stocked(D(10))
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_ITEM_MESSAGE):
        service.record_close(
            state, CloseRequest(close_date=DAY, adjustments=[Adjustment(item_id="it_none", delta=D(1), reason="r")])
        )


def shop(outcome=MockOutcome.ACCEPT, address="서울시 어딘가 1"):
    """구매 품목 '원단'(보유 10m, 단가 1000)과 거래처 하나."""
    state = fresh()
    service.set_settings(state, InventorySettings(address=address))
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회", mock_outcome=outcome))
    [item] = service.add_items(
        state, [draft("원단", kind="material", unit="m", procurement="purchase", supplier_id=supplier.supplier_id, quantity=D(10))]
    )
    service.set_policy(
        state, item.item_id, ReorderPolicy(min_stock=D(20), target_stock=D(50), purchase_unit=D(10), lead_days=3, unit_price=D(1000))
    )
    return state, item.item_id


def order_request(item_id, qty="40", request_id="req-00000001", **line):
    return OrderRequest(request_id=request_id, lines=[{"item_id": item_id, "quantity": qty, **line}])


def test_place_order_accepted_uses_policy_price_and_counts_in_transit():
    state, item = shop()
    order = service.place_order(state, order_request(item), MockSupplier())

    assert order.status is OrderStatus.ACCEPTED and order.origin is OrderOrigin.MANUAL
    assert order.lines[0].unit_price == D(1000) and order.total == D(40000)
    assert order.supplier_ref == "mock-req-00000001"
    assert state.orders == [order]
    assert in_transit(state.orders, item) == D(40)
    assert state.holds == []


def test_same_request_id_returns_existing_order_without_calling_supplier():
    state, item = shop()
    first = service.place_order(state, order_request(item), MockSupplier())

    class Exploding(MockSupplier):
        def place(self, *args):
            raise AssertionError("거래처를 다시 부르면 안 된다")

    again = service.place_order(state, order_request(item, qty="99"), Exploding())
    assert again == first and len(state.orders) == 1


def test_line_unit_price_overrides_policy_price():
    state, item = shop()
    order = service.place_order(state, order_request(item, unit_price="1100"), MockSupplier())
    assert order.total == D(44000)


@pytest.mark.parametrize(
    ("outcome", "status", "hold_reason"),
    [
        (MockOutcome.PRICE_CHANGED, OrderStatus.REJECTED, HoldReason.PRICE_CHANGED),
        (MockOutcome.OUT_OF_STOCK, OrderStatus.REJECTED, HoldReason.OUT_OF_STOCK),
        (MockOutcome.UNKNOWN_THEN_ACCEPT, OrderStatus.UNKNOWN, HoldReason.UNKNOWN),
    ],
)
def test_failed_orders_are_recorded_with_a_hold(outcome, status, hold_reason):
    state, item = shop(outcome)
    order = service.place_order(state, order_request(item), MockSupplier())

    assert order.status is status
    assert [(h.item_id, h.order_id, h.reason) for h in state.holds] == [(item, order.order_id, hold_reason)]
    assert in_transit(state.orders, item) == D(0)


def test_price_changed_hold_keeps_current_price():
    state, item = shop(MockOutcome.PRICE_CHANGED)
    order = service.place_order(state, order_request(item), MockSupplier())
    assert order.reject_reason is RejectReason.PRICE_CHANGED
    assert order.current_prices == {item: D("1100.00")}
    assert state.holds[0].current_unit_price == D("1100.00")


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ("no_address", INVENTORY_ADDRESS_REQUIRED_MESSAGE),
        ("make_item", INVENTORY_NOT_ORDERABLE_MESSAGE),
        ("no_policy", INVENTORY_POLICY_REQUIRED_MESSAGE),
        ("unknown_item", INVENTORY_UNKNOWN_ITEM_MESSAGE),
        ("duplicate_line", INVENTORY_DUPLICATE_LINE_MESSAGE),
        ("mixed_supplier", INVENTORY_MIXED_SUPPLIER_MESSAGE),
    ],
)
def test_place_order_rejections_leave_state_untouched(setup, message):
    state, item = shop(address="" if setup == "no_address" else "서울시 어딘가 1")
    lines = [{"item_id": item, "quantity": "10"}]
    if setup == "make_item":
        [made] = service.add_items(state, [draft("에코백")])
        lines = [{"item_id": made.item_id, "quantity": "1"}]
    if setup == "no_policy":
        [bare] = service.add_items(
            state, [draft("끈", kind="packaging", procurement="purchase", supplier_id=state.suppliers[0].supplier_id)]
        )
        lines = [{"item_id": bare.item_id, "quantity": "1"}]
    if setup == "unknown_item":
        lines = [{"item_id": "it_none", "quantity": "1"}]
    if setup == "duplicate_line":
        lines = lines * 2
    if setup == "mixed_supplier":
        other = service.add_supplier(state, SupplierDraft(name="다른상회"))
        [thread] = service.add_items(
            state, [draft("실", kind="material", procurement="purchase", supplier_id=other.supplier_id)]
        )
        service.set_policy(state, thread.item_id, state.policies[item])
        lines = [*lines, {"item_id": thread.item_id, "quantity": "1"}]
    before = state.model_copy(deep=True)

    with pytest.raises(InventoryError, match=message):
        service.place_order(state, OrderRequest(request_id="req-00000009", lines=lines), MockSupplier())
    assert state == before


def test_refresh_unknown_order_settles_and_resolves_unknown_hold():
    state, item = shop(MockOutcome.UNKNOWN_THEN_ACCEPT)
    order = service.place_order(state, order_request(item), MockSupplier())

    refreshed = service.refresh_order(state, order.order_id, MockSupplier())

    assert refreshed.status is OrderStatus.ACCEPTED and refreshed.supplier_ref == "mock-req-00000001"
    assert state.orders == [refreshed]
    assert [h.resolved for h in state.holds] == [True]
    assert in_transit(state.orders, item) == D(40)


def test_refresh_settled_order_does_not_call_supplier():
    state, item = shop()
    order = service.place_order(state, order_request(item), MockSupplier())

    class Exploding(MockSupplier):
        def lookup(self, *args):
            raise AssertionError("접수 불명이 아니면 다시 묻지 않는다")

    assert service.refresh_order(state, order.order_id, Exploding()) == order
    with pytest.raises(InventoryNotFound, match=INVENTORY_ORDER_NOT_FOUND_MESSAGE):
        service.refresh_order(state, "or_none", MockSupplier())


def test_receive_partial_then_full_and_already_counted():
    state, item = shop()
    order = service.place_order(state, order_request(item), MockSupplier())

    service.receive(state, order.order_id, ReceiptRequest(lines=[{"item_id": item, "quantity": "15"}]))
    assert state.orders[0].status is OrderStatus.PARTIALLY_RECEIVED
    assert on_hand(state.ledger, item) == D(25)
    assert in_transit(state.orders, item) == D(25)

    done = service.receive(
        state, order.order_id, ReceiptRequest(lines=[{"item_id": item, "quantity": "25", "already_counted": True}])
    )
    assert done.status is OrderStatus.RECEIVED
    assert on_hand(state.ledger, item) == D(25)  # 이미 센 물건은 더하지 않는다
    assert in_transit(state.orders, item) == D(0)
    assert isinstance(state.ledger[-1], ReceiptEntry) and state.ledger[-1].order_id == order.order_id


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("over", INVENTORY_OVER_RECEIPT_MESSAGE),
        ("other_item", INVENTORY_RECEIPT_ITEM_MESSAGE),
        ("rejected", INVENTORY_ORDER_NOT_RECEIVABLE_MESSAGE),
    ],
)
def test_receive_rejections_leave_state_untouched(case, message):
    state, item = shop(MockOutcome.OUT_OF_STOCK if case == "rejected" else MockOutcome.ACCEPT)
    order = service.place_order(state, order_request(item), MockSupplier())
    line = {"item_id": item, "quantity": "41" if case == "over" else "1"}
    if case == "other_item":
        line["item_id"] = "it_other"
    before = state.model_copy(deep=True)

    with pytest.raises(InventoryError, match=message):
        service.receive(state, order.order_id, ReceiptRequest(lines=[line]))
    assert state == before


def test_receive_unknown_order_is_not_found():
    state, _ = shop()
    with pytest.raises(InventoryNotFound, match=INVENTORY_ORDER_NOT_FOUND_MESSAGE):
        service.receive(state, "or_none", ReceiptRequest(lines=[{"item_id": "it_x", "quantity": "1"}]))


def test_resolve_hold_is_idempotent_and_unknown_is_not_found():
    state, item = shop(MockOutcome.OUT_OF_STOCK)
    service.place_order(state, order_request(item), MockSupplier())
    hold_id = state.holds[0].hold_id

    assert service.resolve_hold(state, hold_id).resolved is True
    assert service.resolve_hold(state, hold_id).resolved is True
    with pytest.raises(InventoryNotFound, match=INVENTORY_HOLD_NOT_FOUND_MESSAGE):
        service.resolve_hold(state, "ho_none")


def test_same_item_same_reason_open_hold_is_not_duplicated():
    state, item = shop(MockOutcome.OUT_OF_STOCK)
    service.place_order(state, order_request(item, request_id="req-00000001"), MockSupplier())
    service.place_order(state, order_request(item, request_id="req-00000002"), MockSupplier())
    assert len(state.holds) == 1
    service.resolve_hold(state, state.holds[0].hold_id)
    service.place_order(state, order_request(item, request_id="req-00000003"), MockSupplier())
    assert len(state.holds) == 2  # 해결한 뒤 다시 생기면 새로 남긴다


def auto_ready(outcome=MockOutcome.ACCEPT):
    state, item = shop(outcome)
    service.set_auto_order(
        state, item, AutoOrderRequest(enabled=True, consent=True, per_order_limit=D(100000), monthly_limit=D(500000))
    )
    return state, item


def close_to(state, item, qty="5"):
    return service.record_close(
        state, CloseRequest(close_date=date(2026, 11, 8), counts={item: D(qty)}, confirmed=[item])
    )


def test_set_auto_order_requires_consent_supplier_and_policy():
    state, item = shop()
    on = AutoOrderRequest(enabled=True, consent=True, per_order_limit=D(1), monthly_limit=D(1))
    with pytest.raises(InventoryError, match=INVENTORY_CONSENT_REQUIRED_MESSAGE):
        service.set_auto_order(state, item, on.model_copy(update={"consent": False}))
    [made] = service.add_items(state, [draft("에코백")])
    with pytest.raises(InventoryError, match=INVENTORY_NOT_ORDERABLE_MESSAGE):
        service.set_auto_order(state, made.item_id, on)
    with pytest.raises(InventoryNotFound):
        service.set_auto_order(state, "it_none", on)

    setting = service.set_auto_order(state, item, on)
    assert setting.enabled is True and setting.consented_at is not None

    off = service.set_auto_order(state, item, AutoOrderRequest(enabled=False, per_order_limit=D(2), monthly_limit=D(3)))
    assert off.enabled is False and off.consented_at == setting.consented_at  # 끄기는 동의 없이, 기록은 남긴다
    assert state.auto_orders[item].monthly_limit == D(3)


def test_run_auto_orders_places_with_close_request_id_and_reports():
    state, item = auto_ready()
    close = close_to(state, item)

    outcomes = service.run_auto_orders(state, close, MockSupplier())

    [order] = state.orders
    assert order.origin is OrderOrigin.AUTO and order.request_id == f"auto:{close.close_id}:{item}"
    assert order.lines[0].quantity == D(50)  # 목표 50 − 보유 5 = 45 → 10 단위 올림
    assert [(o.item_id, o.order_id, o.status, o.hold_reason) for o in outcomes] == [(item, order.order_id, OrderStatus.ACCEPTED, None)]


def test_run_auto_orders_twice_for_same_close_orders_once():
    state, item = auto_ready()
    close = close_to(state, item)
    service.run_auto_orders(state, close, MockSupplier())
    service.run_auto_orders(state, close, MockSupplier())
    assert len(state.orders) == 1


def test_run_auto_orders_records_holds_for_plan_and_supplier_failures():
    state, item = auto_ready(MockOutcome.OUT_OF_STOCK)
    close = close_to(state, item)
    [outcome] = service.run_auto_orders(state, close, MockSupplier())
    assert outcome.status is OrderStatus.REJECTED and outcome.hold_reason is HoldReason.OUT_OF_STOCK
    assert [h.reason for h in state.holds] == [HoldReason.OUT_OF_STOCK]

    state, item = auto_ready()
    service.set_auto_order(state, item, AutoOrderRequest(enabled=True, consent=True, per_order_limit=D(1), monthly_limit=D(1)))
    close = close_to(state, item)
    [outcome] = service.run_auto_orders(state, close, MockSupplier())
    assert (outcome.order_id, outcome.hold_reason) == (None, HoldReason.LIMIT_EXCEEDED)
    assert state.orders == [] and [h.reason for h in state.holds] == [HoldReason.LIMIT_EXCEEDED]


def test_suggest_then_apply_policy():
    state, item = shop()
    suggestion = service.suggest_policy(state, item, MockProvider())
    assert state.suggestions[item] == suggestion
    assert state.policies[item].min_stock == D(20)  # 추천만으로는 바뀌지 않는다

    applied = service.apply_suggestion(state, item)
    assert (applied.min_stock, applied.target_stock, applied.purchase_unit) == (
        suggestion.min_stock, suggestion.target_stock, suggestion.purchase_unit
    )
    assert (applied.lead_days, applied.unit_price) == (3, D(1000))  # 사용자 값은 그대로
    assert item not in state.suggestions
    with pytest.raises(InventoryNotFound, match=INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE):
        service.apply_suggestion(state, item)


def test_suggest_requires_policy_and_known_item():
    state = fresh()
    [item] = service.add_items(state, [draft()])
    with pytest.raises(InventoryError, match=INVENTORY_POLICY_REQUIRED_MESSAGE):
        service.suggest_policy(state, item.item_id, MockProvider())
    with pytest.raises(InventoryNotFound):
        service.suggest_policy(state, "it_none", MockProvider())


def test_suggest_failure_leaves_state_untouched():
    state, item = shop()
    before = state.model_copy(deep=True)
    with pytest.raises(ProviderError):
        service.suggest_policy(state, item, MockProvider(fail_stages={"inventory_policy"}))
    assert state == before
