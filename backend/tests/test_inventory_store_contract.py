"""InventoryStore 계약. 새 저장소는 store 픽스처에 넣고 이 테스트를 그대로 통과해야 한다."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.state import SessionState
from app.core.store import SqliteSessionStore
from app.inventory.models import CountEntry, InventoryState, Item, ItemKind, Procurement
from app.inventory.store import InMemoryInventoryStore, PostgresInventoryStore, SqliteInventoryStore


@pytest.fixture(params=["memory", "sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryInventoryStore()
    if request.param == "sqlite":
        return SqliteInventoryStore(tmp_path / "sessions.db")
    return PostgresInventoryStore(request.getfixturevalue("postgres_pool"))


def _item() -> Item:
    return Item(name="에코백", kind=ItemKind.FINISHED, unit="개", procurement=Procurement.MAKE)


def test_missing_owner_returns_none(store):
    assert store.get("client-none") is None


def test_save_and_get_round_trip(store):
    state = InventoryState(owner_id="client-aaaa", items=[_item()])
    state.ledger.append(CountEntry(item_id=state.items[0].item_id, quantity=Decimal("2.5")))
    store.save(state)

    loaded = store.get("client-aaaa")

    assert loaded.items == state.items
    assert loaded.ledger[0].quantity == Decimal("2.5")


def test_get_returns_independent_copy(store):
    store.save(InventoryState(owner_id="client-aaaa"))
    loaded = store.get("client-aaaa")
    loaded.items.append(_item())
    assert store.get("client-aaaa").items == []


def test_save_stores_a_copy(store):
    state = InventoryState(owner_id="client-aaaa")
    store.save(state)
    state.items.append(_item())
    assert store.get("client-aaaa").items == []


def test_save_overwrites_and_bumps_updated_at(store):
    long_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
    state = InventoryState(owner_id="client-aaaa", updated_at=long_ago)
    store.save(state)
    state.items.append(_item())
    store.save(state)

    loaded = store.get("client-aaaa")
    assert len(loaded.items) == 1
    assert loaded.updated_at > long_ago


def test_owners_are_separate(store):
    store.save(InventoryState(owner_id="client-aaaa", items=[_item()]))
    store.save(InventoryState(owner_id="client-bbbb"))
    assert len(store.get("client-aaaa").items) == 1
    assert store.get("client-bbbb").items == []


def test_sqlite_session_and_inventory_stores_share_one_file(tmp_path):
    path = tmp_path / "sessions.db"
    sessions = SqliteSessionStore(path)
    inventories = SqliteInventoryStore(path)
    session = SessionState(task_type="t", raw_input="안녕", owner_id="client-aaaa")

    sessions.save(session)
    inventories.save(InventoryState(owner_id="client-aaaa", items=[_item()]))

    assert sessions.get(session.session_id).raw_input == "안녕"
    assert len(inventories.get("client-aaaa").items) == 1
