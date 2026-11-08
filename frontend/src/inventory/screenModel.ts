import type { AnomalyKind, AutoOrderOutcome, InventorySettings, InventoryView, ItemKind, ItemView, StockStatus, Supplier } from "../api/types";
import {
  ANOMALY_LABELS,
  HOLD_LABELS,
  KIND_LABELS,
  moneyText,
  ORDER_STATUS_LABELS,
  PROCUREMENT_LABELS,
  quantityText,
  STATUS_LABELS,
} from "../lib/inventory/format";
import type { InventoryState } from "./state";

type Filter = InventoryState["filter"];
type CloseState = InventoryState["close"];

/** 숨기지 않은 품목 중 이름·옵션 검색(대소문자·앞뒤 공백 무시)과 분류에 맞는 것. */
export function filterItems(items: ItemView[], filter: Filter): ItemView[] {
  const query = filter.query.trim().toLowerCase();
  return items.filter(({ item }) => {
    if (item.archived) return false;
    if (filter.kind !== "all" && item.kind !== filter.kind) return false;
    if (query === "") return true;
    return `${item.name} ${item.option ?? ""}`.toLowerCase().includes(query);
  });
}

// ---- 현황 ----

export type StockRow = {
  itemId: string;
  name: string;
  option: string;
  kind: ItemKind;
  onHand: string;
  inTransit: string;
  status: StockStatus;
  statusLabel: string;
  suggested: string;
};

export type StockModel = { rows: StockRow[]; shortCount: number; uncountedCount: number; lastClose: string | null };

const STATUS_ORDER: Record<StockStatus, number> = { short: 0, uncounted: 1, in_transit: 2, ok: 2 };

export function stockModel(view: InventoryView, filter: Filter): StockModel {
  const shown = filterItems(view.items, filter);
  const rows = [...shown]
    .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.item.name.localeCompare(b.item.name, "ko"))
    .map(
      (v): StockRow => ({
        itemId: v.item.item_id,
        name: v.item.name,
        option: v.item.option ?? "",
        kind: v.item.kind,
        onHand: quantityText(v.on_hand, v.item.unit),
        inTransit: quantityText(v.in_transit, v.item.unit),
        status: v.status,
        statusLabel: STATUS_LABELS[v.status],
        suggested: v.suggested_quantity === null ? "" : quantityText(v.suggested_quantity, v.item.unit),
      }),
    );
  return {
    rows,
    shortCount: shown.filter((v) => v.status === "short").length,
    uncountedCount: shown.filter((v) => v.status === "uncounted").length,
    lastClose: view.last_close?.close_date ?? null,
  };
}

// ---- 마감 ----

export type CloseRow = { itemId: string; name: string; option: string; unit: string; previous: string; input: string };
export type AnomalyRow = {
  itemId: string;
  name: string;
  kind: AnomalyKind;
  kindLabel: string;
  change: string;
  confirmed: boolean;
  adjustment: { delta: string; reason: string };
};
export type CloseResultModel = { summary: string; rows: { itemId: string; name: string; text: string }[] };
export type CloseModel = {
  rows: CloseRow[];
  anomalies: AnomalyRow[];
  canCheck: boolean;
  canSave: boolean;
  result: CloseResultModel | null;
};

const NUMBER = /^-?\d+(\.\d+)?$/;

/** 조정 입력: 비었으면 쓰지 않음(empty), 사유와 0이 아닌 변화량이 다 있으면 ok, 그 밖은 덜 쓴 것(invalid). */
function adjustmentState(adjustment: { delta: string; reason: string }): "empty" | "ok" | "invalid" {
  const delta = adjustment.delta.trim();
  const reason = adjustment.reason.trim();
  if (delta === "" && reason === "") return "empty";
  return NUMBER.test(delta) && Number(delta) !== 0 && reason !== "" ? "ok" : "invalid";
}

function itemOf(view: InventoryView, itemId: string): ItemView["item"] | undefined {
  return view.items.find((v) => v.item.item_id === itemId)?.item;
}

export function autoOrderSummary(outcomes: AutoOrderOutcome[]): string {
  if (outcomes.length === 0) return "자동 주문 없음";
  const orders = outcomes.filter((o) => o.order_id !== null).length;
  const holds = outcomes.filter((o) => o.hold_reason !== null).length;
  return `주문 ${orders}건·보류 ${holds}건`;
}

function outcomeText(outcome: AutoOrderOutcome): string {
  if (outcome.hold_reason !== null) return `보류: ${HOLD_LABELS[outcome.hold_reason]}`;
  return outcome.status === null ? "주문 없음" : ORDER_STATUS_LABELS[outcome.status];
}

export function closeModel(view: InventoryView, close: CloseState, filter: Filter): CloseModel {
  const rows = filterItems(view.items, filter).map(
    (v): CloseRow => ({
      itemId: v.item.item_id,
      name: v.item.name,
      option: v.item.option ?? "",
      unit: v.item.unit,
      previous: quantityText(v.on_hand, v.item.unit),
      input: close.counts[v.item.item_id] ?? "",
    }),
  );
  const anomalies = (close.check?.anomalies ?? []).map((a): AnomalyRow => {
    const item = itemOf(view, a.item_id);
    const unit = item?.unit ?? "";
    return {
      itemId: a.item_id,
      name: item?.name ?? a.item_id,
      kind: a.kind,
      kindLabel: ANOMALY_LABELS[a.kind],
      change: `${quantityText(a.previous, unit)} → ${quantityText(a.counted, unit)}`,
      confirmed: close.confirmed.includes(a.item_id),
      adjustment: close.adjustments[a.item_id] ?? { delta: "", reason: "" },
    };
  });
  const adjustments = Object.values(close.adjustments).map(adjustmentState);
  const hasCounts = Object.values(close.counts).some((text) => text.trim() !== "");
  // 서버 규칙: 이상 수량은 모두 confirmed에 있어야 저장된다(조정은 확인을 대신하지 않는다).
  const canSave =
    close.check !== null &&
    (hasCounts || adjustments.includes("ok")) &&
    anomalies.every((a) => a.confirmed) &&
    !adjustments.includes("invalid");
  return {
    rows,
    anomalies,
    canCheck: hasCounts,
    canSave,
    result:
      close.result === null
        ? null
        : {
            summary: autoOrderSummary(close.result.auto_orders),
            rows: close.result.auto_orders.map((o) => ({
              itemId: o.item_id,
              name: itemOf(view, o.item_id)?.name ?? o.item_id,
              text: outcomeText(o),
            })),
          },
  };
}

// ---- 품목·설정 ----

export type ItemRow = {
  itemId: string;
  name: string;
  option: string;
  kindLabel: string;
  unit: string;
  procurementLabel: string;
  supplierName: string;
  policyText: string;
  suggestion: { label: string; reason: string; text: string } | null;
};
export type ItemsModel = { rows: ItemRow[]; suppliers: Supplier[]; settings: InventorySettings };

export function itemsModel(view: InventoryView): ItemsModel {
  const rows = view.items
    .filter((v) => !v.item.archived)
    .map((v): ItemRow => {
      const { item, policy, suggestion } = v;
      const q = (n: string) => quantityText(n, item.unit);
      return {
        itemId: item.item_id,
        name: item.name,
        option: item.option ?? "",
        kindLabel: KIND_LABELS[item.kind],
        unit: item.unit,
        procurementLabel: PROCUREMENT_LABELS[item.procurement],
        supplierName: view.suppliers.find((s) => s.supplier_id === item.supplier_id)?.name ?? "",
        policyText:
          policy === null
            ? "기준 없음"
            : `최소 ${q(policy.min_stock)} · 목표 ${q(policy.target_stock)} · 구매 단위 ${q(policy.purchase_unit)} · 납기 ${policy.lead_days}일 · 단가 ${moneyText(policy.unit_price)}`,
        suggestion:
          suggestion === null
            ? null
            : {
                label: "확인 전",
                reason: suggestion.reason,
                text: `최소 ${q(suggestion.min_stock)} · 목표 ${q(suggestion.target_stock)} · 구매 단위 ${q(suggestion.purchase_unit)}`,
              },
      };
    });
  return { rows, suppliers: view.suppliers, settings: view.settings };
}
