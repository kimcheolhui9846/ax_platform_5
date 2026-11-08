from datetime import date
from decimal import Decimal as D

import pytest

from app.core.messages import (
    INVENTORY_ADJUST_UNCOUNTED_MESSAGE,
    INVENTORY_EMPTY_CLOSE_MESSAGE,
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_NEGATIVE_STOCK_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    unconfirmed_anomaly_message,
    duplicate_item_message,
)
from app.inventory import service
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import AdjustEntry, CountEntry, InventorySettings, InventoryState, MockOutcome, ReorderPolicy
from app.inventory.rules import AnomalyKind, on_hand
from app.schemas.inventory import Adjustment, CloseRequest, ItemDraft, ItemPatch, SupplierDraft, SupplierPatch


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
