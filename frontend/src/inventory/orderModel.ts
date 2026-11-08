// 주문 관련 화면 모델(순수): 제안·주문 초안·주문 확인·주문 카드·보류·자동 주문.
import type { Hold, InventoryView, ItemView, Order, OrderStatus } from "../api/types";
import {
  HOLD_LABELS,
  lineAmount,
  moneyText,
  ORDER_STATUS_LABELS,
  ORIGIN_LABELS,
  quantityText,
  remainingQuantity,
  sumAmounts,
} from "../lib/inventory/format";
import type { OrderDraft, OrderResultNotice } from "./state";

const byName = (a: string, b: string) => a.localeCompare(b, "ko");

/** 한국 시간 기준 YYYY-MM-DD. */
function dateText(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return iso.slice(0, 10);
  return new Date(time).toLocaleDateString("sv-SE", { timeZone: "Asia/Seoul" });
}

/** 주문할 수 있는 품목(숨기지 않은 구매 품목 + 거래처 + 보충 기준). */
function orderable(v: ItemView): boolean {
  return !v.item.archived && v.item.procurement === "purchase" && v.item.supplier_id !== null && v.policy !== null;
}

function supplierName(view: InventoryView, supplierId: string): string {
  return view.suppliers.find((s) => s.supplier_id === supplierId)?.name ?? "알 수 없는 거래처";
}

const itemOf = (view: InventoryView, itemId: string): ItemView | undefined => view.items.find((v) => v.item.item_id === itemId);

// ---- 제안·초안 ----

export type ProposalGroup = {
  supplierId: string;
  supplierName: string;
  lines: { itemId: string; name: string; unit: string; suggested: string; unitPrice: string }[];
};

export function orderProposals(view: InventoryView): ProposalGroup[] {
  const groups = new Map<string, ProposalGroup>();
  for (const v of view.items) {
    const supplierId = v.item.supplier_id;
    if (!orderable(v) || v.status !== "short" || v.suggested_quantity === null || v.policy === null || supplierId === null) continue;
    const group = groups.get(supplierId) ?? { supplierId, supplierName: supplierName(view, supplierId), lines: [] };
    group.lines.push({ itemId: v.item.item_id, name: v.item.name, unit: v.item.unit, suggested: v.suggested_quantity, unitPrice: v.policy.unit_price });
    groups.set(supplierId, group);
  }
  return [...groups.values()]
    .map((g) => ({ ...g, lines: [...g.lines].sort((a, b) => byName(a.name, b.name)) }))
    .sort((a, b) => byName(a.supplierName, b.supplierName));
}

export function draftFromProposal(group: ProposalGroup, requestId: string): OrderDraft {
  return {
    requestId,
    supplierId: group.supplierId,
    lines: group.lines.map((l) => ({ itemId: l.itemId, quantity: l.suggested, unitPrice: l.unitPrice })),
    repriced: false,
  };
}

export function draftFromHold(view: InventoryView, holdId: string, requestId: string): OrderDraft | null {
  const hold = view.holds.find((h) => h.hold_id === holdId);
  if (hold === undefined || hold.reason !== "price_changed" || hold.current_unit_price === null) return null;
  const item = itemOf(view, hold.item_id);
  if (item === undefined || !orderable(item) || item.item.supplier_id === null) return null;
  const heldOrder = hold.order_id === null ? undefined : view.orders.find((o) => o.order_id === hold.order_id);
  const quantity = heldOrder?.lines.find((l) => l.item_id === hold.item_id)?.quantity ?? item.suggested_quantity;
  if (quantity === null || quantity === undefined) return null;
  return {
    requestId,
    supplierId: item.item.supplier_id,
    lines: [{ itemId: hold.item_id, quantity, unitPrice: hold.current_unit_price }],
    repriced: true,
  };
}

// ---- 주문 확인 카드 ----

export type OrderConfirmModel = {
  supplierName: string;
  address: string;
  addressMissing: boolean;
  lines: { itemId: string; name: string; unit: string; quantity: string; unitPriceText: string; amountText: string; valid: boolean }[];
  totalText: string;
  canSubmit: boolean;
  repriced: boolean;
};

function positiveQuantity(text: string): boolean {
  return /^\d+(\.\d+)?$/.test(text) && Number(text) > 0;
}

export function orderConfirmModel(view: InventoryView, draft: OrderDraft): OrderConfirmModel {
  const address = view.settings.address.trim();
  const lines = draft.lines.map((l) => {
    const item = itemOf(view, l.itemId);
    const valid = positiveQuantity(l.quantity);
    const amount = valid ? lineAmount(l.quantity, l.unitPrice) : null;
    return {
      itemId: l.itemId,
      name: item?.item.name ?? "알 수 없는 품목",
      unit: item?.item.unit ?? "",
      quantity: l.quantity,
      unitPriceText: moneyText(l.unitPrice),
      amountText: amount === null ? "-" : moneyText(amount),
      valid,
      amount,
    };
  });
  return {
    supplierName: supplierName(view, draft.supplierId),
    address,
    addressMissing: address === "",
    lines: lines.map(({ amount: _amount, ...line }) => line),
    totalText: moneyText(sumAmounts(lines.flatMap((l) => (l.amount === null ? [] : [l.amount])))),
    canSubmit: lines.length > 0 && lines.every((l) => l.valid) && address !== "",
    repriced: draft.repriced,
  };
}

export function orderResultText(notice: OrderResultNotice): string {
  switch (notice.status) {
    case "accepted":
      return "주문이 접수됐어요";
    case "rejected":
      return notice.holdReason === null ? "주문이 거절됐어요" : `주문이 거절됐어요: ${HOLD_LABELS[notice.holdReason]}`;
    case "unknown":
      return "접수 여부를 확인하지 못했어요. 주문·입고 탭에서 다시 확인해 주세요";
    default:
      return `${ORDER_STATUS_LABELS[notice.status]}`;
  }
}

export type OrderPanel = { confirm: OrderConfirmModel | null; result: string | null };

// ---- 주문·입고 탭 ----

export type OrderCard = {
  orderId: string;
  supplierName: string;
  originLabel: string;
  statusLabel: string;
  status: OrderStatus;
  createdDate: string;
  totalText: string;
  lines: { itemId: string; name: string; unit: string; ordered: string; received: string; remaining: string; remainingRaw: string }[];
  canRefresh: boolean;
  canReceive: boolean;
};

export function orderCards(view: InventoryView): OrderCard[] {
  return view.orders.map((o) => ({
    orderId: o.order_id,
    supplierName: supplierName(view, o.supplier_id),
    originLabel: ORIGIN_LABELS[o.origin],
    statusLabel: ORDER_STATUS_LABELS[o.status],
    status: o.status,
    createdDate: dateText(o.created_at),
    totalText: moneyText(o.total),
    lines: o.lines.map((l) => {
      const item = itemOf(view, l.item_id);
      const unit = item?.item.unit ?? "";
      const remainingRaw = remainingQuantity(l.quantity, l.received);
      return {
        itemId: l.item_id,
        name: item?.item.name ?? "알 수 없는 품목",
        unit,
        ordered: quantityText(l.quantity, unit),
        received: quantityText(l.received, unit),
        remaining: quantityText(remainingRaw, unit),
        remainingRaw,
      };
    }),
    canRefresh: o.status === "unknown",
    canReceive: o.status === "accepted" || o.status === "partially_received",
  }));
}

// ---- 보류 ----

export type HoldRow = {
  holdId: string;
  itemName: string;
  reasonLabel: string;
  createdDate: string;
  orderId: string | null;
  canReview: boolean;
  canRefresh: boolean;
  priceText: string | null;
};

export function holdRows(view: InventoryView): HoldRow[] {
  return view.holds
    .filter((h) => !h.resolved)
    .map((h) => ({
      holdId: h.hold_id,
      itemName: itemOf(view, h.item_id)?.item.name ?? "알 수 없는 품목",
      reasonLabel: HOLD_LABELS[h.reason],
      createdDate: dateText(h.created_at),
      orderId: h.order_id,
      canReview: draftFromHold(view, h.hold_id, "") !== null,
      canRefresh: view.orders.find((o) => o.order_id === h.order_id)?.status === "unknown",
      priceText: h.current_unit_price === null ? null : moneyText(h.current_unit_price),
    }));
}

// ---- 자동 주문 탭 ----

export type AutoRow = { itemId: string; name: string; orderable: boolean; reason: string; enabled: boolean; limitsText: string; lastResult: string };
export type AutoModel = { rows: AutoRow[]; addressMissing: boolean };

/** 그 품목의 가장 최근 자동 주문 결과(미해결 자동 보류가 더 최근이면 그 사유). */
function lastAutoResult(view: InventoryView, itemId: string): string {
  const time = (iso: string) => Date.parse(iso);
  const orders: Order[] = view.orders.filter((o) => o.origin === "auto" && o.lines.some((l) => l.item_id === itemId));
  const lastOrder = orders.reduce<Order | null>((best, o) => (best === null || time(o.created_at) > time(best.created_at) ? o : best), null);
  const isAutoHold = (h: Hold) => h.item_id === itemId && !h.resolved && (h.order_id === null || view.orders.find((o) => o.order_id === h.order_id)?.origin === "auto");
  const lastHold = view.holds.filter(isAutoHold).reduce<Hold | null>((best, h) => (best === null || time(h.created_at) > time(best.created_at) ? h : best), null);
  if (lastHold !== null && (lastOrder === null || time(lastHold.created_at) > time(lastOrder.created_at))) {
    return `${HOLD_LABELS[lastHold.reason]} · ${dateText(lastHold.created_at)}`;
  }
  if (lastOrder !== null) return `${ORDER_STATUS_LABELS[lastOrder.status]} · ${dateText(lastOrder.created_at)}`;
  return "아직 없음";
}

export function autoRows(view: InventoryView): AutoRow[] {
  return view.items
    .filter((v) => !v.item.archived && v.item.procurement === "purchase")
    .map((v) => {
      const ok = orderable(v);
      const setting = v.auto_order;
      return {
        itemId: v.item.item_id,
        name: v.item.name,
        orderable: ok,
        reason: ok ? "" : "거래처와 보충 기준이 필요해요",
        enabled: setting?.enabled ?? false,
        limitsText: setting === null ? "설정 안 함" : `1회 ${moneyText(setting.per_order_limit)} · 월 ${moneyText(setting.monthly_limit)}`,
        lastResult: lastAutoResult(view, v.item.item_id),
      };
    });
}

export function autoModel(view: InventoryView): AutoModel {
  return { rows: autoRows(view), addressMissing: view.settings.address.trim() === "" };
}
