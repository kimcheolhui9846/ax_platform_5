import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/inventory", () => ({
  getInventory: vi.fn(),
  addItems: vi.fn(),
  updateItem: vi.fn(),
  addSupplier: vi.fn(),
  updateSupplier: vi.fn(),
  setSettings: vi.fn(),
  setPolicy: vi.fn(),
  checkClose: vi.fn(),
  recordClose: vi.fn(),
  suggestPolicy: vi.fn(),
  applySuggestion: vi.fn(),
  placeOrder: vi.fn(),
  refreshOrder: vi.fn(),
  receive: vi.fn(),
  resolveHold: vi.fn(),
  setAutoOrder: vi.fn(),
}));

import { addItems, applySuggestion, checkClose, getInventory, placeOrder, receive, recordClose, refreshOrder, resolveHold, setAutoOrder, setPolicy, suggestPolicy } from "../api/inventory";
import { INVENTORY } from "../preview/fixtures";
import { makeInventoryHandlers } from "./handlers";
import type { InventoryRequest } from "./requests";
import { initialInventoryState } from "./state";
import type { InventoryAction, InventoryState } from "./state";

beforeEach(() => vi.clearAllMocks());

function setup(patch: Partial<InventoryState> = {}, confirm = true) {
  const calls: InventoryRequest<unknown>[] = [];
  const actions: InventoryAction[] = [];
  const tabs: string[] = [];
  let asked = 0;
  let ids = 0;
  const state = { ...initialInventoryState("2026-11-08"), ...patch };
  const on = makeInventoryHandlers({
    state,
    tab: "close",
    run: async <T>(call: InventoryRequest<T>) => {
      calls.push(call as InventoryRequest<unknown>);
    },
    dispatch: (a) => actions.push(a),
    navigate: (tab) => tabs.push(tab),
    newRequestId: () => `manual:${++ids}`,
    confirmLeave: () => {
      asked += 1;
      return confirm;
    },
  });
  return { on, calls, actions, tabs, asked: () => asked };
}

describe("탭 이동", () => {
  it("저장하지 않은 입력이 없으면 묻지 않고 간다", () => {
    const t = setup();
    t.on.onTab("items");
    expect(t.tabs).toEqual(["items"]);
    expect(t.asked()).toBe(0);
  });

  it("같은 탭이면 아무것도 하지 않는다", () => {
    const t = setup({ dirty: true });
    t.on.onTab("close");
    expect(t.tabs).toEqual([]);
    expect(t.asked()).toBe(0);
  });

  it("입력이 있으면 확인하고, 떠나면 저장하지 않은 입력을 버린다", () => {
    const t = setup({ dirty: true });
    t.on.onTab("stock");
    expect(t.asked()).toBe(1);
    expect(t.tabs).toEqual(["stock"]);
    expect(t.actions).toEqual([{ type: "discarded" }]);
  });

  it("마감 입력이 없어도 저장하지 않은 양식 입력이 있으면 묻는다", () => {
    const t = setup({ edited: ["settings"] });
    t.on.onTab("stock");
    expect(t.asked()).toBe(1);
    expect(t.actions).toEqual([{ type: "discarded" }]);
  });

  it("저장한 마감 결과를 둔 채 마감 탭을 떠나면 결과를 비운다(다시 오면 새 마감)", () => {
    const close = { ...initialInventoryState().close, result: {} as never };
    const t = setup({ close });
    t.on.onTab("stock");
    expect(t.asked()).toBe(0);
    expect(t.actions).toEqual([{ type: "closeReset" }]);
    expect(t.tabs).toEqual(["stock"]);
  });

  it("왼쪽 메뉴로 떠날 때도 같은 확인을 거친다", () => {
    const go = vi.fn();
    const kept = setup({ edited: ["settings"] }, false);
    kept.on.onLeave(go);
    expect(go).not.toHaveBeenCalled();
    const left = setup({ edited: ["settings"] });
    left.on.onLeave(go);
    expect(go).toHaveBeenCalledTimes(1);
    expect(left.actions).toEqual([{ type: "discarded" }]);
    const clean = setup();
    clean.on.onLeave(go);
    expect(clean.asked()).toBe(0);
    expect(go).toHaveBeenCalledTimes(2);
  });

  it("확인에서 취소하면 머문다", () => {
    const t = setup({ dirty: true }, false);
    t.on.onTab("stock");
    expect(t.tabs).toEqual([]);
    expect(t.actions).toEqual([]);
  });
});

describe("요청", () => {
  it("불러오기·다시 시도", async () => {
    const t = setup();
    t.on.onRetry();
    expect(t.calls[0].kind).toBe("load");
    await t.calls[0].request();
    expect(getInventory).toHaveBeenCalled();
  });

  it("마감 검사는 빈칸을 뺀 입력을 문자열 그대로 보낸다", async () => {
    const t = setup({ close: { ...initialInventoryState().close, counts: { a: "3", b: "  ", c: "1.50" } } });
    t.on.onCheck();
    expect(t.calls[0].kind).toBe("check");
    await t.calls[0].request();
    expect(checkClose).toHaveBeenCalledWith({ counts: { a: "3", c: "1.50" } });
  });

  it("마감 저장 본문: 입력 날짜·센 수량·확인·완성된 조정만", async () => {
    const close = {
      ...initialInventoryState().close,
      counts: { a: "3", b: "" },
      confirmed: ["a"],
      adjustments: { a: { delta: "-2", reason: "파손" }, z: { delta: "", reason: "" } },
    };
    const t = setup({ close });
    t.on.onSave("2026-11-07");
    expect(t.calls[0].kind).toBe("close");
    await t.calls[0].request();
    expect(recordClose).toHaveBeenCalledWith({
      close_date: "2026-11-07",
      counts: { a: "3" },
      adjustments: [{ item_id: "a", delta: "-2", reason: "파손" }],
      confirmed: ["a"],
    });
    expect(t.calls[0].done({ close: {} } as never, 4).type).toBe("closed");
  });

  it("추천 받기는 suggest 종류, 적용은 policy 양식 저장", async () => {
    const t = setup();
    t.on.onSuggest("i1");
    t.on.onApplySuggestion("i1");
    expect(t.calls.map((c) => [c.kind, c.form])).toEqual([
      ["suggest", undefined],
      ["save", "policy"],
    ]);
    await t.calls[0].request();
    await t.calls[1].request();
    expect(suggestPolicy).toHaveBeenCalledWith("i1");
    expect(applySuggestion).toHaveBeenCalledWith("i1");
  });

  it("저장은 양식 이름을 단다", async () => {
    const t = setup();
    t.on.onCreateItems([{ name: "a", kind: "finished", unit: "개", procurement: "make" }]);
    t.on.onSavePolicy("i1", { min_stock: 1, target_stock: 2, purchase_unit: 1, lead_days: 1, unit_price: 1 });
    expect(t.calls.map((c) => [c.kind, c.form])).toEqual([
      ["save", "bulk"],
      ["save", "policy"],
    ]);
    await t.calls[0].request();
    await t.calls[1].request();
    expect(addItems).toHaveBeenCalled();
    expect(setPolicy).toHaveBeenCalledWith("i1", expect.objectContaining({ lead_days: 1 }));
  });
});

describe("입력 action", () => {
  it("버튼을 action으로 바꾼다", () => {
    const t = setup();
    t.on.onFilter({ query: "x" });
    t.on.onCount("a", "5");
    t.on.onConfirm("a", true);
    t.on.onAdjust("a", "1", "r");
    t.on.onDate("2026-01-01");
    t.on.onReset();
    t.on.onEdited("bulk");
    expect(t.actions.map((a) => a.type)).toEqual(["filterChanged", "countChanged", "anomalyConfirmed", "adjustmentChanged", "closeDateChanged", "closeReset", "edited"]);
    expect(t.actions.at(-1)).toEqual({ type: "edited", form: "bulk" });
  });
});

describe("주문·입고·보류·자동 주문", () => {
  const draft = { requestId: "manual:x", supplierId: "sup-1", lines: [{ itemId: "it-1", quantity: "40", unitPrice: "4500" }], repriced: false };
  const withView = { view: INVENTORY };

  it("주문 확인을 열면 제안 묶음으로 초안을 만든다", () => {
    const t = setup(withView);
    t.on.onOpenOrder("sup-1");
    expect(t.actions).toHaveLength(1);
    expect(t.actions[0]).toMatchObject({ type: "orderOpened", draft: { requestId: "manual:1", supplierId: "sup-1", repriced: false } });
  });
  it("없는 묶음이면 아무것도 하지 않는다", () => {
    const t = setup(withView);
    t.on.onOpenOrder("nope");
    expect(t.actions).toEqual([]);
  });
  it("초안 편집은 액션으로", () => {
    const t = setup(withView);
    t.on.onOrderQuantity("it-1", "5");
    t.on.onOrderRemoveLine("it-1");
    t.on.onOrderCancel();
    t.on.onOrderResultClose();
    expect(t.actions).toEqual([
      { type: "orderQuantityChanged", itemId: "it-1", quantity: "5" },
      { type: "orderLineRemoved", itemId: "it-1" },
      { type: "orderCancelled" },
      { type: "orderResultClosed" },
    ]);
  });
  it("주문하기는 초안의 request_id로 보내고, 기준 단가는 싣지 않는다", async () => {
    const t = setup({ ...withView, order: draft });
    t.on.onPlaceOrder();
    expect(t.calls[0].kind).toBe("order");
    vi.mocked(placeOrder).mockResolvedValue({ ok: true, data: {} as never } as never);
    await t.calls[0].request();
    expect(placeOrder).toHaveBeenCalledWith({ request_id: "manual:x", lines: [{ item_id: "it-1", quantity: "40" }] });
  });
  it("같은 초안을 두 번 보내면 같은 request_id", async () => {
    const t = setup({ ...withView, order: draft });
    t.on.onPlaceOrder();
    t.on.onPlaceOrder();
    await t.calls[0].request();
    await t.calls[1].request();
    const ids = vi.mocked(placeOrder).mock.calls.map((c) => c[0].request_id);
    expect(ids).toEqual(["manual:x", "manual:x"]);
  });
  it("새 단가로 연 초안은 unit_price를 싣는다", async () => {
    const t = setup({ ...withView, order: { ...draft, repriced: true, lines: [{ itemId: "it-1", quantity: "40", unitPrice: "5000" }] } });
    t.on.onPlaceOrder();
    await t.calls[0].request();
    expect(placeOrder).toHaveBeenCalledWith({ request_id: "manual:x", lines: [{ item_id: "it-1", quantity: "40", unit_price: "5000" }] });
  });
  it("주문 응답은 ordered 액션이 된다", () => {
    const t = setup({ ...withView, order: draft });
    t.on.onPlaceOrder();
    const r = { order: { order_id: "o" }, inventory: INVENTORY } as never;
    expect((t.calls[0] as unknown as InventoryRequest<typeof r>).done(r, 7)).toMatchObject({ type: "ordered", seq: 7, view: INVENTORY });
  });
  it("초안이 없거나 보낼 수 없으면 요청하지 않는다", () => {
    const none = setup(withView);
    none.on.onPlaceOrder();
    const bad = setup({ ...withView, order: { ...draft, lines: [{ itemId: "it-1", quantity: "0", unitPrice: "4500" }] } });
    bad.on.onPlaceOrder();
    expect(none.calls).toEqual([]);
    expect(bad.calls).toEqual([]);
  });
  it("다시 확인·입고·보류 해결·자동 주문 저장 요청", async () => {
    const t = setup(withView);
    t.on.onRefreshOrder("o-1");
    t.on.onReceive("o-1", [{ item_id: "it-1", quantity: "3", already_counted: true }]);
    t.on.onResolveHold("h-1");
    const auto = { enabled: true, consent: true, per_order_limit: "10", monthly_limit: "20" };
    t.on.onSaveAutoOrder("it-1", auto);
    expect(t.calls.map((c) => [c.kind, "form" in c ? c.form : undefined])).toEqual([
      ["refresh", undefined],
      ["save", "receipt"],
      ["resolve", undefined],
      ["save", "auto"],
    ]);
    for (const c of t.calls) await c.request();
    expect(refreshOrder).toHaveBeenCalledWith("o-1");
    expect(receive).toHaveBeenCalledWith("o-1", { lines: [{ item_id: "it-1", quantity: "3", already_counted: true }] });
    expect(resolveHold).toHaveBeenCalledWith("h-1");
    expect(setAutoOrder).toHaveBeenCalledWith("it-1", auto);
  });
  it("보류의 새 단가로 다시 주문 / 주문 탭 열기", () => {
    const view = { ...INVENTORY, holds: [{ hold_id: "h-1", item_id: "it-1", order_id: null, reason: "price_changed" as const, current_unit_price: "5000", created_at: "x", resolved: false }] };
    const t = setup({ view });
    t.on.onReviewHold("h-1");
    t.on.onReviewHold("nope");
    t.on.onOpenOrders();
    expect(t.actions).toHaveLength(1);
    expect(t.actions[0]).toMatchObject({ type: "orderOpened", draft: { repriced: true } });
    expect(t.tabs).toEqual(["orders"]);
  });
  it("주문 탭 열기도 탭 이동과 같다: 저장하지 않은 입력을 묻고, 마감 결과를 지운다", () => {
    const kept = setup({ edited: ["receipt"] }, false);
    kept.on.onOpenOrders();
    expect(kept.asked()).toBe(1);
    expect(kept.tabs).toEqual([]);
    const result = { ...initialInventoryState("2026-11-08").close, result: {} as never };
    const reset = setup({ close: result });
    reset.on.onOpenOrders();
    expect(reset.actions).toContainEqual({ type: "closeReset" });
    expect(reset.tabs).toEqual(["orders"]);
  });
  it("주문·입고 탭으로 가면 주문 결과 안내를 닫는다(그 탭이 안내가 가리키는 곳이다)", () => {
    const t = setup({ orderResult: { status: "unknown", holdReason: "unknown" } });
    t.on.onOpenOrders();
    expect(t.actions).toContainEqual({ type: "orderResultClosed" });
    const other = setup({ orderResult: { status: "accepted", holdReason: null } });
    other.on.onTab("stock");
    expect(other.actions).not.toContainEqual({ type: "orderResultClosed" });
  });
});
