from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.inventory.models import (
    AdjustEntry,
    AutoOrderSetting,
    Close,
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
    PolicySuggestion,
    Procurement,
    ReceiptEntry,
    ReorderPolicy,
    Supplier,
)


def _item(**overrides) -> Item:
    values = {"name": "에코백", "kind": ItemKind.FINISHED, "unit": "개", "procurement": Procurement.MAKE}
    return Item(**(values | overrides))


def test_new_state_is_empty_with_default_settings():
    state = InventoryState(owner_id="client-aaaa")
    assert state.items == [] and state.ledger == [] and state.closes == []
    assert state.settings.anomaly_drop_ratio == Decimal("0.5")
    assert state.settings.stale_days == 7
    assert state.settings.address == ""


def test_ids_have_prefixes():
    assert _item().item_id.startswith("it_")
    assert CountEntry(item_id="it_x", quantity=Decimal(1)).entry_id.startswith("le_")
    assert Close(close_date=date(2026, 11, 8), counts={}).close_id.startswith("cl_")


def test_ledger_round_trips_through_json_with_its_type():
    state = InventoryState(owner_id="client-aaaa", items=[_item()])
    item_id = state.items[0].item_id
    state.ledger = [
        CountEntry(item_id=item_id, quantity=Decimal("10")),
        AdjustEntry(item_id=item_id, delta=Decimal("-2.5"), reason="파손"),
    ]

    loaded = InventoryState.model_validate_json(state.model_dump_json())

    assert [type(e) for e in loaded.ledger] == [CountEntry, AdjustEntry]
    assert loaded.ledger[1].delta == Decimal("-2.5")


@pytest.mark.parametrize("quantity", ["-1", "1.234"])
def test_count_quantity_is_non_negative_with_two_decimals(quantity):
    with pytest.raises(ValidationError):
        CountEntry(item_id="it_x", quantity=Decimal(quantity))


def test_policy_purchase_unit_must_be_positive():
    with pytest.raises(ValidationError):
        ReorderPolicy(min_stock=1, target_stock=2, purchase_unit=0, lead_days=3, unit_price=1000)


def test_exponent_input_is_written_as_plain_decimal():
    policy = ReorderPolicy(min_stock=1, target_stock=2, purchase_unit=1, lead_days=3, unit_price="1e3")
    assert policy.model_dump(mode="json")["unit_price"] == "1000"


def test_plain_decimals_keep_their_value():
    policy = ReorderPolicy(min_stock="0.5", target_stock="7.5", purchase_unit=1, lead_days=0, unit_price=0)
    assert policy.min_stock == Decimal("0.5")
    assert policy.target_stock == Decimal("7.5")


def test_close_counts_reject_negative():
    with pytest.raises(ValidationError):
        Close(close_date=date(2026, 11, 8), counts={"it_x": Decimal("-1")})


@pytest.mark.parametrize("ratio", ["0", "1.01"])
def test_settings_reject_bad_anomaly_ratio(ratio):
    with pytest.raises(ValidationError):
        InventorySettings(anomaly_drop_ratio=Decimal(ratio))


@pytest.mark.parametrize("days", [0, 91])
def test_settings_reject_bad_stale_days(days):
    with pytest.raises(ValidationError):
        InventorySettings(stale_days=days)


def test_new_state_has_empty_order_collections():
    state = InventoryState(owner_id="client-aaaa")
    assert state.orders == [] and state.holds == []
    assert state.auto_orders == {} and state.suggestions == {}


def test_old_document_without_order_fields_still_loads():
    old = '{"owner_id": "client-aaaa", "items": [], "ledger": [{"type": "count", "item_id": "it_a", "quantity": "3"}]}'
    state = InventoryState.model_validate_json(old)
    assert state.orders == [] and state.ledger[0].quantity == Decimal(3)


def test_receipt_and_order_round_trip():
    order = Order(
        request_id="req-00000001",
        supplier_id="sup_a",
        lines=[OrderLine(item_id="it_a", quantity=Decimal(10), unit_price=Decimal(1000))],
        total=Decimal(10000),
        origin=OrderOrigin.MANUAL,
        status=OrderStatus.ACCEPTED,
    )
    state = InventoryState(owner_id="client-aaaa", orders=[order])
    state.ledger.append(ReceiptEntry(item_id="it_a", quantity=Decimal(4), order_id=order.order_id))
    state.holds.append(Hold(item_id="it_a", reason=HoldReason.STALE_COUNT))
    state.auto_orders["it_a"] = AutoOrderSetting(per_order_limit=Decimal(50000), monthly_limit=Decimal(200000))
    state.suggestions["it_a"] = PolicySuggestion(
        min_stock=Decimal(5), target_stock=Decimal(20), purchase_unit=Decimal(10), reason="최근 소진량 기준"
    )

    loaded = InventoryState.model_validate_json(state.model_dump_json())

    assert order.order_id.startswith("or_") and state.holds[0].hold_id.startswith("ho_")
    assert isinstance(loaded.ledger[0], ReceiptEntry) and loaded.ledger[0].already_counted is False
    assert loaded.orders[0].lines[0].received == Decimal(0)
    assert loaded.auto_orders["it_a"].enabled is False
    assert loaded == state


def test_empty_names_units_and_reasons_are_rejected():
    with pytest.raises(ValidationError):
        _item(name="")
    with pytest.raises(ValidationError):
        _item(unit="")
    with pytest.raises(ValidationError):
        Supplier(name="")
    with pytest.raises(ValidationError):
        AdjustEntry(item_id="it_x", delta=Decimal(1), reason="")
