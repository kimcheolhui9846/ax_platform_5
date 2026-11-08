import { describe, expect, it } from "vitest";
import type { AutoOrderOutcome, CloseView, InventoryView, ItemView } from "../api/types";
import { EMPTY_CLOSE, type InventoryState } from "./state";
import { autoOrderSummary, closeModel, filterItems, itemsModel, stockModel } from "./screenModel";

function item(id: string, name: string, over: Partial<ItemView> = {}, itemOver: Partial<ItemView["item"]> = {}): ItemView {
  return {
    item: { item_id: id, name, option: null, kind: "material", unit: "m", procurement: "purchase", supplier_id: null, archived: false, ...itemOver },
    on_hand: "10",
    in_transit: "0",
    status: "ok",
    suggested_quantity: null,
    policy: null,
    last_counted_at: null,
    suggestion: null,
    auto_order: null,
    ...over,
  };
}

function view(items: ItemView[], over: Partial<InventoryView> = {}): InventoryView {
  return {
    items,
    suppliers: [],
    settings: { address: "", anomaly_drop_ratio: "0.5", stale_days: 7 },
    last_close: null,
    orders: [],
    holds: [],
    ...over,
  };
}

const NO_FILTER: InventoryState["filter"] = { query: "", kind: "all" };

describe("filterItems", () => {
  const items = [
    item("a", "Cotton Fabric", {}, { option: "Blue" }),
    item("b", "상자", {}, { kind: "packaging" }),
    item("c", "숨김", {}, { archived: true }),
  ];
  it("숨긴 품목은 늘 뺀다", () => {
    expect(filterItems(items, NO_FILTER).map((i) => i.item.item_id)).toEqual(["a", "b"]);
  });
  it("이름·옵션 부분 일치는 대소문자와 앞뒤 공백을 무시", () => {
    expect(filterItems(items, { query: "  cotton ", kind: "all" })).toHaveLength(1);
    expect(filterItems(items, { query: "BLU", kind: "all" })).toHaveLength(1);
    expect(filterItems(items, { query: "없음", kind: "all" })).toHaveLength(0);
  });
  it("분류로 거른다", () => {
    expect(filterItems(items, { query: "", kind: "packaging" }).map((i) => i.item.item_id)).toEqual(["b"]);
  });
});

describe("stockModel", () => {
  it("부족 먼저, 미입력, 그다음 이름순. 미입력은 0이 아니다", () => {
    const v = view([
      item("a", "나", { status: "ok" }),
      item("b", "가", { status: "uncounted", on_hand: null }),
      item("c", "다", { status: "short", suggested_quantity: "20" }),
      item("d", "라", { status: "short" }),
      item("e", "마", { status: "in_transit", in_transit: "5" }),
    ]);
    const m = stockModel(v, NO_FILTER);
    expect(m.rows.map((r) => r.itemId)).toEqual(["c", "d", "b", "a", "e"]);
    expect(m.shortCount).toBe(2);
    expect(m.uncountedCount).toBe(1);
    const unc = m.rows.find((r) => r.itemId === "b")!;
    expect(unc.onHand).toBe("미입력");
    expect(unc.statusLabel).toBe("미입력");
    expect(m.rows.find((r) => r.itemId === "c")!.suggested).toBe("20 m");
    expect(m.rows.find((r) => r.itemId === "a")!.suggested).toBe("");
    expect(m.rows.find((r) => r.itemId === "e")!.inTransit).toBe("5 m");
  });
  it("부족·미입력 개수는 필터와 상관없이 숨기지 않은 전체 품목 기준", () => {
    const v = view([
      item("a", "가", { status: "short" }),
      item("b", "나", { status: "uncounted", on_hand: null }, { kind: "packaging" }),
      item("c", "다", { status: "short" }, { archived: true }),
    ]);
    const m = stockModel(v, { query: "없는검색어", kind: "packaging" });
    expect(m.rows).toHaveLength(0);
    expect(m.shortCount).toBe(1);
    expect(m.uncountedCount).toBe(1);
  });
  it("마지막 마감 날짜", () => {
    expect(stockModel(view([]), NO_FILTER).lastClose).toBeNull();
    const close = { close_id: "x", close_date: "2026-11-01", counts: {}, at: "2026-11-01T00:00:00Z" };
    expect(stockModel(view([], { last_close: close }), NO_FILTER).lastClose).toBe("2026-11-01");
  });
});

describe("closeModel", () => {
  const v = view([item("a", "가", { on_hand: "10" }), item("b", "나", { on_hand: null, status: "uncounted" })]);
  const anomaly = { item_id: "a", previous: "10", counted: "30", kind: "increase" as const };
  const base = (over: Partial<InventoryState["close"]> = {}) => ({ ...EMPTY_CLOSE, ...over });

  it("행은 지난 수량과 입력 칸 값을 갖는다", () => {
    const m = closeModel(v, base({ counts: { a: "7" } }), NO_FILTER);
    expect(m.rows).toEqual([
      expect.objectContaining({ itemId: "a", name: "가", previous: "10 m", input: "7" }),
      expect.objectContaining({ itemId: "b", previous: "미입력", input: "" }),
    ]);
  });
  it("canCheck는 입력이 하나라도 있을 때", () => {
    expect(closeModel(v, base(), NO_FILTER).canCheck).toBe(false);
    expect(closeModel(v, base({ counts: { a: "7" } }), NO_FILTER).canCheck).toBe(true);
    expect(closeModel(v, base({ counts: { a: "  " } }), NO_FILTER).canCheck).toBe(false);
  });
  it("검사 전에는 저장할 수 없다", () => {
    const m = closeModel(v, base({ counts: { a: "7" } }), NO_FILTER);
    expect(m.canSave).toBe(false);
    expect(m.anomalies).toEqual([]);
  });
  it("이상 수량이 없으면 검사 뒤 저장 가능", () => {
    const m = closeModel(v, base({ counts: { a: "7" }, check: { anomalies: [] } }), NO_FILTER);
    expect(m.canSave).toBe(true);
  });
  it("이상 수량은 모두 확인되어야 저장 가능(조정만으로는 안 된다)", () => {
    const check = { anomalies: [anomaly] };
    const counts = { a: "30" };
    expect(closeModel(v, base({ counts, check }), NO_FILTER).canSave).toBe(false);
    expect(closeModel(v, base({ counts, check, adjustments: { a: { delta: "-1", reason: "파손" } } }), NO_FILTER).canSave).toBe(false);
    const ok = closeModel(v, base({ counts, check, confirmed: ["a"] }), NO_FILTER);
    expect(ok.canSave).toBe(true);
    expect(ok.anomalies).toEqual([
      expect.objectContaining({ itemId: "a", name: "가", kindLabel: "지난번보다 늘었어요", change: "10 m → 30 m", confirmed: true }),
    ]);
  });
  it("조정은 사유와 0이 아닌 변화량이 있어야 하고, 반쯤 쓴 조정은 저장을 막는다", () => {
    const withCheck = (adjustments: InventoryState["close"]["adjustments"]) =>
      closeModel(v, base({ counts: { a: "7" }, check: { anomalies: [] }, adjustments }), NO_FILTER);
    expect(withCheck({ a: { delta: "-2", reason: "파손" } }).canSave).toBe(true);
    expect(withCheck({ a: { delta: "-2", reason: " " } }).canSave).toBe(false);
    expect(withCheck({ a: { delta: "0", reason: "그냥" } }).canSave).toBe(false);
    expect(withCheck({ a: { delta: "abc", reason: "그냥" } }).canSave).toBe(false);
    expect(withCheck({ a: { delta: "", reason: "" } }).canSave).toBe(true);
  });
  it("숫자가 아니거나 음수인 수량이 하나라도 있으면 검사·저장 모두 막는다", () => {
    for (const bad of ["abc", "-1", "1e3"]) {
      const m = closeModel(v, base({ counts: { a: "7", b: bad }, check: { anomalies: [] } }), NO_FILTER);
      expect(m.canCheck).toBe(false);
      expect(m.canSave).toBe(false);
    }
    expect(closeModel(v, base({ counts: { a: "0", b: "2.5" }, check: { anomalies: [] } }), NO_FILTER).canCheck).toBe(true);
  });
  it("주문과 보류가 함께 있는 결과는 보류 한 건으로만 센다", () => {
    const auto: AutoOrderOutcome[] = [
      { item_id: "a", order_id: "o1", status: "rejected", hold_reason: "out_of_stock" },
      { item_id: "b", order_id: "o2", status: "accepted", hold_reason: null },
    ];
    expect(autoOrderSummary(auto)).toBe("주문 1건·보류 1건");
  });
  it("없는 품목은 알 수 없는 품목으로 보인다", () => {
    const result = { close: {}, inventory: v, auto_orders: [{ item_id: "zzz", order_id: null, status: null, hold_reason: null }] } as unknown as CloseView;
    expect(closeModel(v, base({ result }), NO_FILTER).result?.rows[0].name).toBe("알 수 없는 품목");
  });
  it("저장 결과는 자동 주문 요약 문장과 행", () => {
    const auto: AutoOrderOutcome[] = [
      { item_id: "a", order_id: "o1", status: "accepted", hold_reason: null },
      { item_id: "b", order_id: null, status: null, hold_reason: "limit_exceeded" },
    ];
    const result = { close: {}, inventory: v, auto_orders: auto } as unknown as CloseView;
    const m = closeModel(v, base({ result }), NO_FILTER);
    expect(m.result?.summary).toBe("주문 1건·보류 1건");
    expect(m.result?.rows).toEqual([
      expect.objectContaining({ itemId: "a", name: "가", text: "주문 접수" }),
      expect.objectContaining({ itemId: "b", name: "나", text: expect.stringContaining("보류") }),
    ]);
    expect(closeModel(v, base({ result: { ...result, auto_orders: [] } }), NO_FILTER).result?.summary).toBe("자동 주문 없음");
    expect(closeModel(v, base(), NO_FILTER).result).toBeNull();
  });
});

describe("itemsModel", () => {
  it("품목 행·거래처·설정·기준과 추천", () => {
    const policy = { min_stock: "5", target_stock: "20", purchase_unit: "10", lead_days: 3, unit_price: "1500" };
    const suggestion = { min_stock: "6", target_stock: "24", purchase_unit: "10", reason: "최근 사용량 기준", created_at: "2026-11-01T00:00:00Z" };
    const sup = { supplier_id: "s1", name: "거래처", kind: "mock" as const, mock_outcome: "accept" as const };
    const v = view(
      [item("a", "가", { policy, suggestion }, { supplier_id: "s1" }), item("b", "나"), item("c", "숨김", {}, { archived: true })],
      { suppliers: [sup] },
    );
    const m = itemsModel(v);
    expect(m.rows.map((r) => r.itemId)).toEqual(["a", "b"]);
    expect(m.rows[0]).toMatchObject({ kindLabel: "재료", procurementLabel: "구매", supplierName: "거래처", unit: "m" });
    expect(m.rows[0].policyText).toBe("최소 5 m · 목표 20 m · 구매 단위 10 m · 납기 3일 · 단가 1,500원");
    expect(m.rows[0].suggestion).toEqual({ label: "확인 전", reason: "최근 사용량 기준", text: "최소 6 m · 목표 24 m · 구매 단위 10 m" });
    expect(m.rows[1].policyText).toBe("기준 없음");
    expect(m.rows[1].suggestion).toBeNull();
    expect(m.rows[1].supplierName).toBe("");
    expect(m.suppliers).toEqual([sup]);
    expect(m.settings).toBe(v.settings);
  });
});
