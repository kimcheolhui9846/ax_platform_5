"""재고 상태 변경은 이 모듈 한 곳에서 한다. 판단은 rules.py(순수)에 맡긴다.

함수는 받은 state를 고친다. 규칙에 어긋나면 InventoryError(422)·InventoryNotFound(404)를 던지고,
라우터는 그때 저장하지 않으므로(복사본을 고치고 성공해야 저장) 요청은 원자적이다.
"""
from collections.abc import Mapping, Sequence
from decimal import Decimal

from app.core.messages import (
    INVENTORY_ADDRESS_REQUIRED_MESSAGE,
    INVENTORY_CONSENT_REQUIRED_MESSAGE,
    INVENTORY_ADJUST_UNCOUNTED_MESSAGE,
    INVENTORY_DUPLICATE_LINE_MESSAGE,
    INVENTORY_HOLD_NOT_FOUND_MESSAGE,
    INVENTORY_MIXED_SUPPLIER_MESSAGE,
    INVENTORY_NOT_ORDERABLE_MESSAGE,
    INVENTORY_ORDER_NOT_FOUND_MESSAGE,
    INVENTORY_ORDER_NOT_RECEIVABLE_MESSAGE,
    INVENTORY_OVER_RECEIPT_MESSAGE,
    INVENTORY_POLICY_REQUIRED_MESSAGE,
    INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE,
    INVENTORY_RECEIPT_ITEM_MESSAGE,
    INVENTORY_EMPTY_CLOSE_MESSAGE,
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_NEGATIVE_STOCK_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    duplicate_item_message,
    unconfirmed_anomaly_message,
)
from app.core.results import utcnow
from app.inventory import advisor
from app.providers.base import LLMProvider
from app.inventory.errors import InventoryError, InventoryNotFound
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
    Order,
    OrderLine,
    OrderOrigin,
    OrderStatus,
    PolicySuggestion,
    Procurement,
    ReceiptEntry,
    RejectReason,
    ReorderPolicy,
    Supplier,
)
from app.inventory.rules import OPEN_STATUSES, Anomaly, AutoAction, plan_auto_orders, find_anomalies, on_hand, daily_usage
from app.inventory.supplier import ReplyStatus, SupplierProvider, SupplierReply
from app.schemas.inventory import (
    AutoOrderOutcome,
    AutoOrderRequest,
    CloseRequest,
    ItemDraft,
    ItemPatch,
    OrderRequest,
    ReceiptRequest,
    SupplierDraft,
    SupplierPatch,
)

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


def _active_item_ids(state: InventoryState) -> set[str]:
    return {i.item_id for i in state.items if not i.archived}


def check_close(state: InventoryState, counts: Mapping[str, Decimal]) -> list[Anomaly]:
    """저장하지 않고 이상 수량만 찾는다."""
    return find_anomalies(state.ledger, counts, state.settings.anomaly_drop_ratio)


def record_close(state: InventoryState, request: CloseRequest) -> Close:
    """검사를 모두 끝낸 뒤에만 state를 고친다(실패하면 그대로)."""
    if not request.counts and not request.adjustments:
        raise InventoryError(INVENTORY_EMPTY_CLOSE_MESSAGE)
    active = _active_item_ids(state)
    touched = set(request.counts) | {a.item_id for a in request.adjustments}
    if not touched <= active:
        raise InventoryError(INVENTORY_UNKNOWN_ITEM_MESSAGE)

    confirmed = set(request.confirmed)
    unconfirmed = [a for a in check_close(state, request.counts) if a.item_id not in confirmed]
    if unconfirmed:
        raise InventoryError(unconfirmed_anomaly_message(find_item(state, a.item_id).name for a in unconfirmed))

    close = Close(close_date=request.close_date, counts=dict(request.counts))
    entries = [CountEntry(item_id=i, quantity=q, close_id=close.close_id) for i, q in request.counts.items()]
    entries += [
        AdjustEntry(item_id=a.item_id, delta=a.delta, reason=a.reason, close_id=close.close_id)
        for a in request.adjustments
    ]
    ledger = [*state.ledger, *entries]
    for item_id in {a.item_id for a in request.adjustments}:
        result = on_hand(ledger, item_id)
        if result is None:
            raise InventoryError(INVENTORY_ADJUST_UNCOUNTED_MESSAGE)
        if result < 0:
            raise InventoryError(INVENTORY_NEGATIVE_STOCK_MESSAGE)

    state.ledger = ledger
    state.closes.append(close)
    return close


_REJECT_HOLDS = {RejectReason.PRICE_CHANGED: HoldReason.PRICE_CHANGED, RejectReason.OUT_OF_STOCK: HoldReason.OUT_OF_STOCK}


def find_order(state: InventoryState, order_id: str) -> Order:
    for order in state.orders:
        if order.order_id == order_id:
            return order
    raise InventoryNotFound(INVENTORY_ORDER_NOT_FOUND_MESSAGE)


def _replace_order(state: InventoryState, order: Order) -> None:
    state.orders = [order if o.order_id == order.order_id else o for o in state.orders]


def _hold(
    state: InventoryState, item_id: str, reason: HoldReason, order_id: str | None = None, current_unit_price: Decimal | None = None
) -> None:
    """같은 품목·같은 사유의 미해결 보류가 있으면 새로 만들지 않는다."""
    if any(h.item_id == item_id and h.reason is reason and not h.resolved for h in state.holds):
        return
    state.holds.append(Hold(item_id=item_id, reason=reason, order_id=order_id, current_unit_price=current_unit_price))


def _hold_for_reply(state: InventoryState, order: Order) -> None:
    """거절·접수 불명이면 주문의 품목마다 보류를 남긴다."""
    for line in order.lines:
        if order.status is OrderStatus.UNKNOWN:
            _hold(state, line.item_id, HoldReason.UNKNOWN, order.order_id)
        elif order.status is OrderStatus.REJECTED and order.reject_reason is not None:
            _hold(state, line.item_id, _REJECT_HOLDS[order.reject_reason], order.order_id, order.current_prices.get(line.item_id))


def _applied(order: Order, reply: SupplierReply) -> Order:
    status = {ReplyStatus.ACCEPTED: OrderStatus.ACCEPTED, ReplyStatus.REJECTED: OrderStatus.REJECTED, ReplyStatus.UNKNOWN: OrderStatus.UNKNOWN}[reply.status]
    return order.model_copy(
        update={
            "status": status,
            "reject_reason": reply.reason,
            "current_prices": dict(reply.current_prices),
            "supplier_ref": reply.supplier_ref,
            "updated_at": utcnow(),
        }
    )


def _orderable(state: InventoryState, item_id: str) -> Item:
    item = next((i for i in state.items if i.item_id == item_id and not i.archived), None)
    if item is None:
        raise InventoryError(INVENTORY_UNKNOWN_ITEM_MESSAGE)
    if item.procurement is not Procurement.PURCHASE or item.supplier_id is None:
        raise InventoryError(INVENTORY_NOT_ORDERABLE_MESSAGE)
    if item_id not in state.policies:
        raise InventoryError(INVENTORY_POLICY_REQUIRED_MESSAGE)
    return item


def _submit(
    state: InventoryState,
    *,
    request_id: str,
    supplier_id: str,
    lines: list[OrderLine],
    origin: OrderOrigin,
    supplier: SupplierProvider,
) -> Order:
    """거래처에 넣고 결과를 주문으로 남긴다. 거절·접수 불명은 보류도 남긴다(검사는 부르기 전에 끝낸다)."""
    target = _find_supplier(state, supplier_id)
    draft = Order(
        request_id=request_id,
        supplier_id=supplier_id,
        lines=lines,
        total=sum((line.quantity * line.unit_price for line in lines), Decimal(0)),
        origin=origin,
        status=OrderStatus.UNKNOWN,
    )
    order = _applied(draft, supplier.place(target, request_id, lines, state.settings.address))
    state.orders.append(order)
    _hold_for_reply(state, order)
    return order


def place_order(state: InventoryState, request: OrderRequest, supplier: SupplierProvider) -> Order:
    existing = next((o for o in state.orders if o.request_id == request.request_id), None)
    if existing is not None:
        return existing
    if not state.settings.address:
        raise InventoryError(INVENTORY_ADDRESS_REQUIRED_MESSAGE)
    item_ids = [line.item_id for line in request.lines]
    if len(set(item_ids)) != len(item_ids):
        raise InventoryError(INVENTORY_DUPLICATE_LINE_MESSAGE)
    items = [_orderable(state, item_id) for item_id in item_ids]
    if len({i.supplier_id for i in items}) != 1:
        raise InventoryError(INVENTORY_MIXED_SUPPLIER_MESSAGE)
    lines = [
        OrderLine(
            item_id=line.item_id,
            quantity=line.quantity,
            unit_price=line.unit_price if line.unit_price is not None else state.policies[line.item_id].unit_price,
        )
        for line in request.lines
    ]
    return _submit(
        state, request_id=request.request_id, supplier_id=items[0].supplier_id, lines=lines, origin=OrderOrigin.MANUAL, supplier=supplier
    )


def refresh_order(state: InventoryState, order_id: str, supplier: SupplierProvider) -> Order:
    """접수 불명 주문만 거래처에 다시 묻는다(다시 주문하지 않는다). 그 밖에는 그대로 돌려준다."""
    order = find_order(state, order_id)
    if order.status is not OrderStatus.UNKNOWN:
        return order
    target = _find_supplier(state, order.supplier_id)
    updated = _applied(order, supplier.lookup(target, order.request_id, order.lines))
    if updated.status is OrderStatus.UNKNOWN:
        return order
    _replace_order(state, updated)
    state.holds = [
        h.model_copy(update={"resolved": True}) if h.order_id == order_id and h.reason is HoldReason.UNKNOWN else h
        for h in state.holds
    ]
    _hold_for_reply(state, updated)
    return updated


def receive(state: InventoryState, order_id: str, request: ReceiptRequest) -> Order:
    order = find_order(state, order_id)
    if order.status not in OPEN_STATUSES:
        raise InventoryError(INVENTORY_ORDER_NOT_RECEIVABLE_MESSAGE)
    received = {line.item_id: line.received for line in order.lines}
    remaining = {line.item_id: line.quantity - line.received for line in order.lines}
    for line in request.lines:
        if line.item_id not in remaining:
            raise InventoryError(INVENTORY_RECEIPT_ITEM_MESSAGE)
        if line.quantity > remaining[line.item_id]:
            raise InventoryError(INVENTORY_OVER_RECEIPT_MESSAGE)
        remaining[line.item_id] -= line.quantity
        received[line.item_id] += line.quantity
    lines = [line.model_copy(update={"received": received[line.item_id]}) for line in order.lines]
    done = all(line.received == line.quantity for line in lines)
    updated = order.model_copy(
        update={"lines": lines, "status": OrderStatus.RECEIVED if done else OrderStatus.PARTIALLY_RECEIVED, "updated_at": utcnow()}
    )
    state.ledger.extend(
        ReceiptEntry(item_id=line.item_id, quantity=line.quantity, order_id=order_id, already_counted=line.already_counted)
        for line in request.lines
    )
    _replace_order(state, updated)
    return updated


def resolve_hold(state: InventoryState, hold_id: str) -> Hold:
    hold = next((h for h in state.holds if h.hold_id == hold_id), None)
    if hold is None:
        raise InventoryNotFound(INVENTORY_HOLD_NOT_FOUND_MESSAGE)
    resolved = hold.model_copy(update={"resolved": True})
    state.holds = [resolved if h.hold_id == hold_id else h for h in state.holds]
    return resolved


def set_auto_order(state: InventoryState, item_id: str, request: AutoOrderRequest) -> AutoOrderSetting:
    item = find_item(state, item_id)
    previous = state.auto_orders.get(item_id)
    consented_at = previous.consented_at if previous else None
    if request.enabled:
        if not request.consent:
            raise InventoryError(INVENTORY_CONSENT_REQUIRED_MESSAGE)
        if item.procurement is not Procurement.PURCHASE or item.supplier_id is None:
            raise InventoryError(INVENTORY_NOT_ORDERABLE_MESSAGE)
        if item_id not in state.policies:
            raise InventoryError(INVENTORY_POLICY_REQUIRED_MESSAGE)
        consented_at = utcnow()
    setting = AutoOrderSetting(
        enabled=request.enabled,
        consented_at=consented_at,
        per_order_limit=request.per_order_limit,
        monthly_limit=request.monthly_limit,
    )
    state.auto_orders[item_id] = setting
    return setting


def run_auto_orders(state: InventoryState, close: Close, supplier: SupplierProvider) -> list[AutoOrderOutcome]:
    """하루 마감 직후 부른다. 같은 마감으로 다시 불러도 request_id가 같아 주문이 두 번 나가지 않는다."""
    outcomes: list[AutoOrderOutcome] = []
    for decision in plan_auto_orders(state, utcnow()):
        if decision.action is AutoAction.HOLD:
            _hold(state, decision.item_id, decision.reason)
            outcomes.append(AutoOrderOutcome(item_id=decision.item_id, order_id=None, status=None, hold_reason=decision.reason))
            continue
        request_id = f"auto:{close.close_id}:{decision.item_id}"
        order = next((o for o in state.orders if o.request_id == request_id), None)
        if order is None:
            item = find_item(state, decision.item_id)
            line = OrderLine(item_id=item.item_id, quantity=decision.quantity, unit_price=state.policies[item.item_id].unit_price)
            order = _submit(
                state, request_id=request_id, supplier_id=item.supplier_id, lines=[line], origin=OrderOrigin.AUTO, supplier=supplier
            )
        hold = next((h for h in state.holds if h.order_id == order.order_id and not h.resolved), None)
        outcomes.append(
            AutoOrderOutcome(item_id=decision.item_id, order_id=order.order_id, status=order.status, hold_reason=hold.reason if hold else None)
        )
    return outcomes


def suggest_policy(state: InventoryState, item_id: str, llm: LLMProvider) -> PolicySuggestion:
    """AI 추천을 받아 '확인 전'으로 둔다. 기준(배송 기간·단가)이 있어야 한다. 실패하면 state는 그대로다."""
    item = find_item(state, item_id)
    policy = state.policies.get(item_id)
    if policy is None:
        raise InventoryError(INVENTORY_POLICY_REQUIRED_MESSAGE)
    prompt = advisor.render_prompt(item, policy, on_hand(state.ledger, item_id), daily_usage(state.ledger, item_id))
    suggestion = advisor.suggest(llm, prompt)
    state.suggestions[item_id] = suggestion
    return suggestion


def apply_suggestion(state: InventoryState, item_id: str) -> ReorderPolicy:
    """추천의 최소·목표·구매 단위를 기준에 반영하고 추천을 지운다(배송 기간·단가는 그대로)."""
    find_item(state, item_id)
    suggestion = state.suggestions.get(item_id)
    if suggestion is None:
        raise InventoryNotFound(INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE)
    current = state.policies.get(item_id)
    if current is None:
        raise InventoryError(INVENTORY_POLICY_REQUIRED_MESSAGE)
    policy = current.model_copy(
        update={"min_stock": suggestion.min_stock, "target_stock": suggestion.target_stock, "purchase_unit": suggestion.purchase_unit}
    )
    state.policies[item_id] = policy
    del state.suggestions[item_id]
    return policy
