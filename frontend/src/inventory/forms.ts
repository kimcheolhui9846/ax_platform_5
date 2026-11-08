import type { AutoOrderRequest, AutoOrderSetting, InventorySettingsRequest, ItemDraft, ItemKind, ItemView, Procurement, ReorderPolicyRequest } from "../api/types";
import type { OrderCard } from "./orderModel";

export const MAX_BULK_ROWS = 200;

/** 일괄 등록 표의 한 줄(입력 중인 글). */
export type BulkRow = {
  name: string;
  option: string;
  kind: ItemKind;
  unit: string;
  procurement: Procurement;
  supplierId: string;
  quantity: string;
};

export function emptyBulkRow(): BulkRow {
  return { name: "", option: "", kind: "material", unit: "", procurement: "purchase", supplierId: "", quantity: "" };
}

const QUANTITY = /^\d+(\.\d+)?$/;

/** 사용자가 아무것도 바꾸지 않은 줄(기본값 그대로). 하나라도 바꿨으면 빈 줄이 아니라서 검사에서 걸린다. */
function rowIsBlank(row: BulkRow): boolean {
  const blank = emptyBulkRow();
  return (Object.keys(blank) as (keyof BulkRow)[]).every((key) => row[key].trim() === blank[key]);
}

function rowIsValid(row: BulkRow): boolean {
  return row.name.trim() !== "" && row.unit.trim() !== "" && (row.quantity.trim() === "" || QUANTITY.test(row.quantity.trim()));
}

/** 빈 줄은 건너뛰고, 쓴 줄이 모두 올바르면 등록할 목록을 준다(아니면 null). */
export function bulkDrafts(rows: BulkRow[]): ItemDraft[] | null {
  const filled = rows.filter((row) => !rowIsBlank(row));
  if (filled.length === 0 || !filled.every(rowIsValid)) return null;
  return filled.map((row) => ({
    name: row.name.trim(),
    option: row.option.trim() === "" ? null : row.option.trim(),
    kind: row.kind,
    unit: row.unit.trim(),
    procurement: row.procurement,
    supplier_id: row.supplierId === "" ? null : row.supplierId,
    quantity: row.quantity.trim() === "" ? null : row.quantity.trim(),
  }));
}

export type PolicyFields = { min: string; target: string; unit: string; lead: string; price: string };

const WHOLE = /^\d+$/;

/** 보충 기준 입력이 모두 올바르면 요청, 아니면 null. 목표는 최소 이상이어야 한다는 건 서버가 정한다. */
export function policyRequest(f: PolicyFields): ReorderPolicyRequest | null {
  const q = [f.min, f.target, f.unit, f.price].map((t) => t.trim());
  if (!q.every((t) => QUANTITY.test(t)) || !WHOLE.test(f.lead.trim())) return null;
  return { min_stock: q[0], target_stock: q[1], purchase_unit: q[2], lead_days: Number(f.lead.trim()), unit_price: q[3] };
}

export type SettingsFields = { address: string; ratio: string; staleDays: string };

export function settingsRequest(f: SettingsFields): InventorySettingsRequest | null {
  if (!QUANTITY.test(f.ratio.trim()) || !WHOLE.test(f.staleDays.trim())) return null;
  return { address: f.address.trim(), anomaly_drop_ratio: f.ratio.trim(), stale_days: Number(f.staleDays.trim()) };
}

// ---- 입고 양식 ----

export type ReceiptFieldLine = { itemId: string; quantity: string; alreadyCounted: boolean };

/** 입고 양식의 처음 값: 남은 수량이 있는 줄만, 수량은 남은 수량으로. */
export function receiptStart(card: OrderCard): ReceiptFieldLine[] {
  return card.lines
    .filter((l) => Number(l.remainingRaw) > 0)
    .map((l) => ({ itemId: l.itemId, quantity: l.remainingRaw, alreadyCounted: false }));
}

/** 빈 칸 줄은 보내지 않고, 쓴 줄이 모두 양수여야 한다. 쓴 줄이 없으면 null. */
export type ReceiptBody = { lines: { item_id: string; quantity: string; already_counted: boolean }[] };

export function receiptRequest(lines: ReceiptFieldLine[]): ReceiptBody | null {
  const filled = lines.filter((l) => l.quantity.trim() !== "");
  if (filled.length === 0 || !filled.every((l) => QUANTITY.test(l.quantity.trim()) && Number(l.quantity.trim()) > 0)) return null;
  return { lines: filled.map((l) => ({ item_id: l.itemId, quantity: l.quantity.trim(), already_counted: l.alreadyCounted })) };
}

/** 입고 양식은 입고 저장이 성공했거나 주문의 입고 수량이 바뀌면 처음 값으로 다시 시작한다. */
export function receiptFormKey(saved: number, card: OrderCard): string {
  return `${saved}:${card.orderId}:${card.lines.map((l) => l.received).join(",")}`;
}

// ---- 자동 주문 양식 ----

export type AutoFields = { enabled: boolean; consent: boolean; perOrder: string; monthly: string };

export const DEFAULT_PER_ORDER_LIMIT = "100000";
export const DEFAULT_MONTHLY_LIMIT = "300000";

const MONEY = /^\d+(\.\d{1,2})?$/;

/** 설정이 있으면 그 값, 없으면 꺼짐과 시작 한도(서버가 한도를 필수로 받는다). */
export function autoOrderStart(setting: AutoOrderSetting | null): AutoFields {
  return {
    enabled: setting?.enabled ?? false,
    consent: setting?.consented_at != null,
    perOrder: setting?.per_order_limit ?? DEFAULT_PER_ORDER_LIMIT,
    monthly: setting?.monthly_limit ?? DEFAULT_MONTHLY_LIMIT,
  };
}

/** 한도가 금액 글이고, 켜려면 동의했을 때만 요청이 된다. */
export function autoOrderRequest(f: AutoFields): AutoOrderRequest | null {
  const perOrder = f.perOrder.trim();
  const monthly = f.monthly.trim();
  if (!MONEY.test(perOrder) || !MONEY.test(monthly) || (f.enabled && !f.consent)) return null;
  return { enabled: f.enabled, consent: f.consent, per_order_limit: perOrder, monthly_limit: monthly };
}

/** 자동 주문 양식은 저장이 성공했거나 그 품목의 설정이 바뀌면 처음 값으로 다시 시작한다. */
export function autoFormKey(saved: number, item: ItemView): string {
  return `${saved}:${item.item.item_id}:${JSON.stringify(item.auto_order)}`;
}
