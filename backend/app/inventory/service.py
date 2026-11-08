"""재고 상태 변경은 이 모듈 한 곳에서 한다. 판단은 rules.py(순수)에 맡긴다.

함수는 받은 state를 고친다. 규칙에 어긋나면 InventoryError(422)·InventoryNotFound(404)를 던지고,
라우터는 그때 저장하지 않으므로(복사본을 고치고 성공해야 저장) 요청은 원자적이다.
"""
from collections.abc import Sequence

from app.core.messages import (
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    duplicate_item_message,
)
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import (
    CountEntry,
    InventorySettings,
    InventoryState,
    Item,
    Procurement,
    ReorderPolicy,
    Supplier,
)
from app.schemas.inventory import ItemDraft, ItemPatch, SupplierDraft, SupplierPatch

_KEEP_WHEN_NULL = ("name", "kind", "unit", "procurement", "archived")


def find_item(state: InventoryState, item_id: str) -> Item:
    for item in state.items:
        if item.item_id == item_id:
            return item
    raise InventoryNotFound(INVENTORY_ITEM_NOT_FOUND_MESSAGE)


def _find_supplier(state: InventoryState, supplier_id: str) -> Supplier:
    for supplier in state.suppliers:
        if supplier.supplier_id == supplier_id:
            return supplier
    raise InventoryNotFound(INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE)


def _checked_supplier(state: InventoryState, procurement: Procurement, supplier_id: str | None) -> str | None:
    """제작 품목은 거래처가 없다. 구매 품목의 거래처는 있어야 한다(본문 안의 잘못된 참조라 422)."""
    if procurement is Procurement.MAKE or supplier_id is None:
        return None
    if not any(s.supplier_id == supplier_id for s in state.suppliers):
        raise InventoryError(INVENTORY_UNKNOWN_SUPPLIER_MESSAGE)
    return supplier_id


def _ensure_unique(items: Sequence[Item]) -> None:
    """숨기지 않은 품목끼리 이름·옵션이 겹치면 안 된다."""
    seen: set[tuple[str, str | None]] = set()
    for item in items:
        if item.archived:
            continue
        key = (item.name, item.option)
        if key in seen:
            raise InventoryError(duplicate_item_message(item.name))
        seen.add(key)


def add_items(state: InventoryState, drafts: Sequence[ItemDraft]) -> list[Item]:
    added = [
        Item(
            name=d.name,
            option=d.option,
            kind=d.kind,
            unit=d.unit,
            procurement=d.procurement,
            supplier_id=_checked_supplier(state, d.procurement, d.supplier_id),
        )
        for d in drafts
    ]
    _ensure_unique([*state.items, *added])
    state.items.extend(added)
    for item, d in zip(added, drafts):
        if d.quantity is not None:
            state.ledger.append(CountEntry(item_id=item.item_id, quantity=d.quantity))
    return added


def update_item(state: InventoryState, item_id: str, patch: ItemPatch) -> Item:
    item = find_item(state, item_id)
    changes = {
        name: getattr(patch, name)
        for name in patch.model_fields_set
        if not (name in _KEEP_WHEN_NULL and getattr(patch, name) is None)
    }
    if "unit" in changes and changes["unit"] != item.unit and any(e.item_id == item_id for e in state.ledger):
        raise InventoryError(INVENTORY_UNIT_LOCKED_MESSAGE)
    updated = item.model_copy(update=changes)
    updated.supplier_id = _checked_supplier(state, updated.procurement, updated.supplier_id)
    others = [i for i in state.items if i.item_id != item_id]
    _ensure_unique([*others, updated])
    state.items = [updated if i.item_id == item_id else i for i in state.items]
    return updated


def add_supplier(state: InventoryState, draft: SupplierDraft) -> Supplier:
    supplier = Supplier(name=draft.name, mock_outcome=draft.mock_outcome)
    state.suppliers.append(supplier)
    return supplier


def update_supplier(state: InventoryState, supplier_id: str, patch: SupplierPatch) -> Supplier:
    supplier = _find_supplier(state, supplier_id)
    changes = {name: getattr(patch, name) for name in patch.model_fields_set if getattr(patch, name) is not None}
    updated = supplier.model_copy(update=changes)
    state.suppliers = [updated if s.supplier_id == supplier_id else s for s in state.suppliers]
    return updated


def set_settings(state: InventoryState, settings: InventorySettings) -> None:
    state.settings = settings


def set_policy(state: InventoryState, item_id: str, policy: ReorderPolicy) -> None:
    find_item(state, item_id)
    if policy.target_stock < policy.min_stock:
        raise InventoryError(INVENTORY_TARGET_BELOW_MIN_MESSAGE)
    state.policies[item_id] = policy
