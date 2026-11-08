from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.inventory.models import (
    AdjustEntry,
    Close,
    CountEntry,
    InventoryState,
    Item,
    ItemKind,
    Procurement,
    ReorderPolicy,
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
