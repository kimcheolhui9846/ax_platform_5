"""재고 API. 상태 변경은 app/inventory/service.py, 응답은 app/inventory/views.py가 한다.

바꾸는 요청은 owner별 잠금 안에서 저장된 묶음의 복사본을 고치고, 끝까지 성공했을 때만 저장한다
(InventoryError·InventoryNotFound면 저장하지 않으므로 원자적이다). 묶음이 없으면 빈 묶음으로 시작한다.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter

from app.api.deps import Inventories, InventoryLocks, Owner
from app.api.locks import SessionLocks
from app.api.responses import error_responses
from app.inventory import service
from app.inventory.models import InventoryState
from app.inventory.store import InventoryStore
from app.inventory.views import to_inventory_view
from app.schemas.inventory import (
    BulkItemsRequest,
    CloseCheckRequest,
    CloseCheckView,
    CloseRequest,
    CloseView,
    InventorySettingsRequest,
    InventoryView,
    ItemDraft,
    ItemPatch,
    ReorderPolicyRequest,
    SupplierDraft,
    SupplierPatch,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], responses=error_responses(500))


def _load(store: InventoryStore, owner: str) -> InventoryState:
    return store.get(owner) or InventoryState(owner_id=owner)


@contextmanager
def _update(locks: SessionLocks, store: InventoryStore, owner: str) -> Iterator[InventoryState]:
    with locks.hold(owner):
        state = _load(store, owner)
        yield state
        store.save(state)


@router.get("", response_model=InventoryView, responses=error_responses(422))
def get_inventory(store: Inventories, owner: Owner) -> InventoryView:
    return to_inventory_view(_load(store, owner))


@router.post("/items/bulk", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_items(body: BulkItemsRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    """S01 일괄 등록. 전부 되거나 전부 안 된다."""
    with _update(locks, store, owner) as state:
        service.add_items(state, body.items)
    return to_inventory_view(state)


@router.post("/items", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_item(body: ItemDraft, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.add_items(state, [body])
    return to_inventory_view(state)


@router.patch("/items/{item_id}", response_model=InventoryView, responses=error_responses(404, 422))
def update_item(item_id: str, body: ItemPatch, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.update_item(state, item_id, body)
    return to_inventory_view(state)


@router.post("/suppliers", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_supplier(body: SupplierDraft, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.add_supplier(state, body)
    return to_inventory_view(state)


@router.patch("/suppliers/{supplier_id}", response_model=InventoryView, responses=error_responses(404, 422))
def update_supplier(
    supplier_id: str, body: SupplierPatch, store: Inventories, locks: InventoryLocks, owner: Owner
) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.update_supplier(state, supplier_id, body)
    return to_inventory_view(state)


@router.put("/settings", response_model=InventoryView, responses=error_responses(422))
def set_settings(body: InventorySettingsRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_settings(state, body)
    return to_inventory_view(state)


@router.put("/items/{item_id}/policy", response_model=InventoryView, responses=error_responses(404, 422))
def set_policy(item_id: str, body: ReorderPolicyRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_policy(state, item_id, body)
    return to_inventory_view(state)


@router.post("/closes/check", response_model=CloseCheckView, responses=error_responses(422))
def check_close(body: CloseCheckRequest, store: Inventories, owner: Owner) -> CloseCheckView:
    """저장하지 않고 이상 수량만 돌려준다(S05-check)."""
    return CloseCheckView(anomalies=service.check_close(_load(store, owner), body.counts))


@router.post("/closes", response_model=CloseView, status_code=201, responses=error_responses(422))
def record_close(body: CloseRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> CloseView:
    with _update(locks, store, owner) as state:
        close = service.record_close(state, body)
    return CloseView(close=close, inventory=to_inventory_view(state))
