import type { InventorySettingsRequest, ItemDraft, ItemKind, Procurement, ReorderPolicyRequest } from "../api/types";

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
