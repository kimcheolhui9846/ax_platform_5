"""재고 API. 상태 변경은 app/inventory/service.py, 응답은 app/inventory/views.py가 한다.

바꾸는 요청은 owner별 잠금 안에서 저장된 묶음의 복사본을 고치고, 끝까지 성공했을 때만 저장한다
(InventoryError·InventoryNotFound면 저장하지 않으므로 원자적이다). 묶음이 없으면 빈 묶음으로 시작한다.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter

from app.api.deps import LLM, Inventories, InventoryLocks, Owner, SupplierDep
from app.api.locks import SessionLocks
from app.api.responses import error_responses
from app.inventory import service
from app.inventory.models import InventorySettings, InventoryState, ReorderPolicy
from app.inventory.store import InventoryStore
from app.inventory.views import to_inventory_view
from app.schemas.inventory import (
    AutoOrderRequest,
    BulkItemsRequest,
    CloseCheckRequest,
    CloseCheckView,
    CloseRequest,
    CloseView,
    InventorySettingsRequest,
    InventoryView,
    ItemDraft,
    ItemPatch,
    OrderRequest,
    OrderView,
    ReceiptRequest,
    ReorderPolicyRequest,
    SupplierDraft,
    SupplierPatch,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], responses=error_responses(500))


def _load(store: InventoryStore, owner: str) -> InventoryState:
    return store.get(owner) or InventoryState(owner_id=owner)


@contextmanager
def _update(locks: SessionLocks, store: InventoryStore, owner: str) -> Iterator[InventoryState]:
    # 잠금 키는 owner id다(서로 다른 client id 수로 한정). 요청이 실패해도 잠금은 만들어질 수 있다.
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
        service.set_settings(state, InventorySettings.model_validate(body.model_dump()))
    return to_inventory_view(state)


@router.put("/items/{item_id}/policy", response_model=InventoryView, responses=error_responses(404, 422))
def set_policy(item_id: str, body: ReorderPolicyRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_policy(state, item_id, ReorderPolicy.model_validate(body.model_dump()))
    return to_inventory_view(state)


@router.post("/closes/check", response_model=CloseCheckView, responses=error_responses(422))
def check_close(body: CloseCheckRequest, store: Inventories, owner: Owner) -> CloseCheckView:
    """저장하지 않고 이상 수량만 돌려준다(S05-check)."""
    return CloseCheckView(anomalies=service.check_close(_load(store, owner), body.counts))


@router.post("/closes", response_model=CloseView, status_code=201, responses=error_responses(422))
def record_close(body: CloseRequest, store: Inventories, locks: InventoryLocks, supplier: SupplierDep, owner: Owner) -> CloseView:
    """S05 하루 마감. 저장한 직후 같은 잠금 안에서 자동 주문을 돌린다(주문 결과와 상관없이 마감은 저장된다).

    거래처가 예외를 내도 run_auto_orders는 그 주문을 접수 불명으로 남기므로 마감은 저장된다. 마감 검사(422)가
    실패하면 자동 주문은 돌지 않고 아무것도 저장되지 않는다.
    """
    with _update(locks, store, owner) as state:
        close = service.record_close(state, body)
        outcomes = service.run_auto_orders(state, close, supplier)
    return CloseView(close=close, inventory=to_inventory_view(state), auto_orders=outcomes)


@router.post("/orders", response_model=OrderView, status_code=201, responses=error_responses(422))
def place_order(body: OrderRequest, store: Inventories, locks: InventoryLocks, supplier: SupplierDep, owner: Owner) -> OrderView:
    """S07 주문 확인. 같은 request_id면 거래처를 다시 부르지 않고 기존 주문을 돌려준다."""
    with _update(locks, store, owner) as state:
        order = service.place_order(state, body, supplier)
    return OrderView(order=order, inventory=to_inventory_view(state))


@router.post("/orders/{order_id}/refresh", response_model=OrderView, responses=error_responses(404, 422))
def refresh_order(order_id: str, store: Inventories, locks: InventoryLocks, supplier: SupplierDep, owner: Owner) -> OrderView:
    """S10 상태 재조회. 접수 불명 주문만 거래처에 다시 묻는다(다시 주문하지 않는다)."""
    with _update(locks, store, owner) as state:
        order = service.refresh_order(state, order_id, supplier)
    return OrderView(order=order, inventory=to_inventory_view(state))


@router.post("/orders/{order_id}/receipts", response_model=OrderView, responses=error_responses(404, 422))
def receive(order_id: str, body: ReceiptRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> OrderView:
    with _update(locks, store, owner) as state:
        order = service.receive(state, order_id, body)
    return OrderView(order=order, inventory=to_inventory_view(state))


@router.post("/holds/{hold_id}/resolve", response_model=InventoryView, responses=error_responses(404, 422))
def resolve_hold(hold_id: str, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.resolve_hold(state, hold_id)
    return to_inventory_view(state)


@router.put("/items/{item_id}/auto-order", response_model=InventoryView, responses=error_responses(404, 422))
def set_auto_order(item_id: str, body: AutoOrderRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_auto_order(state, item_id, body)
    return to_inventory_view(state)


@router.post("/items/{item_id}/policy/suggestion", response_model=InventoryView, responses=error_responses(404, 422, 502, 503))
def suggest_policy(item_id: str, store: Inventories, locks: InventoryLocks, llm: LLM, owner: Owner) -> InventoryView:
    """S03 AI 추천 받기. 추천은 '확인 전'으로 두고 기준은 바꾸지 않는다."""
    with _update(locks, store, owner) as state:
        service.suggest_policy(state, item_id, llm)
    return to_inventory_view(state)


@router.post("/items/{item_id}/policy/suggestion/apply", response_model=InventoryView, responses=error_responses(404, 422))
def apply_suggestion(item_id: str, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.apply_suggestion(state, item_id)
    return to_inventory_view(state)
