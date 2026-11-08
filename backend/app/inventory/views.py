"""재고 상태 → 응답(순수). 수량·상태·제안량은 rules.py가 계산하고 화면은 다시 계산하지 않는다."""
from app.inventory.models import InventoryState, Item
from app.inventory.rules import in_transit as in_transit_of
from app.inventory.rules import item_status, last_counted_at, on_hand, suggested_quantity
from app.schemas.inventory import InventoryView, ItemView


def _item_view(state: InventoryState, item: Item) -> ItemView:
    quantity = on_hand(state.ledger, item.item_id)
    policy = state.policies.get(item.item_id)
    in_transit = in_transit_of(state.orders, item.item_id)
    return ItemView(
        item=item,
        on_hand=quantity,
        in_transit=in_transit,
        status=item_status(quantity, in_transit, policy),
        suggested_quantity=suggested_quantity(quantity, in_transit, policy),
        policy=policy,
        last_counted_at=last_counted_at(state.ledger, item.item_id),
        suggestion=state.suggestions.get(item.item_id),
        auto_order=state.auto_orders.get(item.item_id),
    )


def to_inventory_view(state: InventoryState) -> InventoryView:
    return InventoryView(
        items=[_item_view(state, item) for item in state.items],
        suppliers=state.suppliers,
        settings=state.settings,
        last_close=state.closes[-1] if state.closes else None,
        orders=sorted(state.orders, key=lambda o: o.created_at, reverse=True),
        holds=sorted(state.holds, key=lambda h: (h.resolved, -h.created_at.timestamp())),
    )
