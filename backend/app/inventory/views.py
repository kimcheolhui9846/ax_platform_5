"""재고 상태 → 응답(순수). 수량·상태·제안량은 rules.py가 계산하고 화면은 다시 계산하지 않는다."""
from decimal import Decimal

from app.inventory.models import InventoryState, Item
from app.inventory.rules import item_status, last_counted_at, on_hand, suggested_quantity
from app.schemas.inventory import InventoryView, ItemView

_NOTHING_IN_TRANSIT = Decimal(0)  # 주문은 PR #41에서 생긴다. 그때 rules.in_transit(state.orders, item_id)로 바꾼다


def _item_view(state: InventoryState, item: Item) -> ItemView:
    quantity = on_hand(state.ledger, item.item_id)
    policy = state.policies.get(item.item_id)
    in_transit = _NOTHING_IN_TRANSIT
    return ItemView(
        item=item,
        on_hand=quantity,
        in_transit=in_transit,
        status=item_status(quantity, in_transit, policy),
        suggested_quantity=suggested_quantity(quantity, in_transit, policy),
        policy=policy,
        last_counted_at=last_counted_at(state.ledger, item.item_id),
    )


def to_inventory_view(state: InventoryState) -> InventoryView:
    return InventoryView(
        items=[_item_view(state, item) for item in state.items],
        suppliers=state.suppliers,
        settings=state.settings,
        last_close=state.closes[-1] if state.closes else None,
    )
