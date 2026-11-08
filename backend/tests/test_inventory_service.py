from decimal import Decimal as D

import pytest

from app.core.messages import (
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    duplicate_item_message,
)
from app.inventory import service
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import CountEntry, InventorySettings, InventoryState, ItemKind, MockOutcome, Procurement, ReorderPolicy
from app.inventory.rules import on_hand
from app.schemas.inventory import ItemDraft, ItemPatch, SupplierDraft, SupplierPatch


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
