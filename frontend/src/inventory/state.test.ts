import { describe, expect, it } from "vitest";
import type { CloseCheckView, CloseView, InventoryView, Order } from "../api/types";
import { hasUnsaved, initialInventoryState, inventoryReducer } from "./state";
import type { InventoryAction, InventoryState, OrderDraft } from "./state";

const view = (tag: string) => ({ tag }) as unknown as InventoryView;
const check = { anomalies: [] } as CloseCheckView;
const result = (tag: string) => ({ inventory: view(tag), auto_orders: [] }) as unknown as CloseView;

function run(actions: InventoryAction[], from: InventoryState = initialInventoryState()): InventoryState {
  return actions.reduce(inventoryReducer, from);
}

describe("inventoryReducer 요청 번호", () => {
  it("늦게 온 응답은 버린다", () => {
    const s = run([
      { type: "requested", seq: 1, kind: "load" },
      { type: "requested", seq: 2, kind: "load" },
    ]);
    expect(inventoryReducer(s, { type: "loaded", seq: 1, view: view("old") })).toBe(s);
    expect(inventoryReducer(s, { type: "failed", seq: 1, message: "x" })).toBe(s);
    expect(inventoryReducer(s, { type: "checked", seq: 1, check })).toBe(s);
    expect(inventoryReducer(s, { type: "closed", seq: 1, result: result("old") })).toBe(s);
  });

  it("지금 번호의 응답은 받고 inflight를 푼다", () => {
    const s = run([
      { type: "requested", seq: 1, kind: "load" },
      { type: "loaded", seq: 1, view: view("a") },
    ]);
    expect(s.view).toEqual(view("a"));
    expect(s.inflight).toBeNull();
    expect(s.loadFailed).toBe(false);
  });
});

describe("inventoryReducer 실패", () => {
  it("처음 불러오기 실패는 loadFailed", () => {
    const s = run([
      { type: "requested", seq: 1, kind: "load" },
      { type: "failed", seq: 1, message: "끊김" },
    ]);
    expect(s.loadFailed).toBe(true);
    expect(s.toast).toBe("끊김");
  });

  it("저장 실패는 입력을 지우지 않는다", () => {
    const s = run([
      { type: "countChanged", itemId: "a", text: "5" },
      { type: "requested", seq: 1, kind: "close" },
      { type: "failed", seq: 1, message: "실패" },
    ]);
    expect(s.close.counts).toEqual({ a: "5" });
    expect(hasUnsaved(s)).toBe(true);
    expect(s.inflight).toBeNull();
    expect(s.loadFailed).toBe(false);
  });
});

describe("inventoryReducer 마감 입력", () => {
  it("수량을 바꾸면 dirty이고 검사 결과가 무효가 된다", () => {
    const s = run([
      { type: "requested", seq: 1, kind: "check" },
      { type: "checked", seq: 1, check },
      { type: "anomalyConfirmed", itemId: "a", confirmed: true },
      { type: "countChanged", itemId: "a", text: "3" },
    ]);
    expect(s.close.check).toBeNull();
    expect(s.close.confirmed).toEqual([]);
    expect(hasUnsaved(s)).toBe(true);
  });

  it("빈칸으로 바꾸면 미입력으로 뺀다", () => {
    const s = run([
      { type: "countChanged", itemId: "a", text: "3" },
      { type: "countChanged", itemId: "a", text: "" },
    ]);
    expect(s.close.counts).toEqual({});
  });

  it("확인을 켜고 끈다", () => {
    const on = run([{ type: "anomalyConfirmed", itemId: "a", confirmed: true }]);
    expect(on.close.confirmed).toEqual(["a"]);
    expect(inventoryReducer(on, { type: "anomalyConfirmed", itemId: "a", confirmed: false }).close.confirmed).toEqual([]);
  });

  it("조정 입력을 둔다", () => {
    const s = run([{ type: "adjustmentChanged", itemId: "a", delta: "-2", reason: "파손" }]);
    expect(s.close.adjustments).toEqual({ a: { delta: "-2", reason: "파손" } });
    expect(hasUnsaved(s)).toBe(true);
  });

  it("마감을 저장하면 입력을 비우고 결과·현황을 갱신한다", () => {
    const s = run([
      { type: "countChanged", itemId: "a", text: "3" },
      { type: "requested", seq: 1, kind: "close" },
      { type: "closed", seq: 1, result: result("new") },
    ]);
    expect(s.close.counts).toEqual({});
    expect(s.close.result).toEqual(result("new"));
    expect(s.view).toEqual(view("new"));
    expect(hasUnsaved(s)).toBe(false);
  });

  it("closeReset은 입력과 결과를 비운다", () => {
    const s = run([{ type: "countChanged", itemId: "a", text: "3" }, { type: "closeReset" }]);
    expect(s.close.counts).toEqual({});
    expect(hasUnsaved(s)).toBe(false);
  });
});

describe("inventoryReducer 그 밖", () => {
  it("필터는 일부만 바꾼다", () => {
    const s = run([
      { type: "filterChanged", filter: { query: "우유" } },
      { type: "filterChanged", filter: { kind: "material" } },
    ]);
    expect(s.filter).toEqual({ query: "우유", kind: "material" });
  });

  it("edited, toastClosed", () => {
    const edited = run([{ type: "edited", form: "bulk" }]);
    expect(hasUnsaved(edited)).toBe(true);
    const toasted = run([
      { type: "requested", seq: 1, kind: "save" },
      { type: "failed", seq: 1, message: "m" },
    ]);
    expect(inventoryReducer(toasted, { type: "toastClosed" }).toast).toBeNull();
  });
});

describe("inventoryReducer 저장 횟수·마감 날짜", () => {
  it("저장이 성공한 응답에서만 그 양식의 횟수가 는다", () => {
    const base = initialInventoryState("2026-11-08");
    const save = (form: "bulk" | "settings" | "receipt" | "auto") => [
      { type: "requested", seq: 1, kind: "save", form } as const,
      { type: "loaded", seq: 1, view: view("a") } as const,
    ];
    const settings = run(save("settings"), base);
    expect(settings.saved).toEqual({ bulk: 0, item: 0, supplier: 0, policy: 0, settings: 1, receipt: 0, auto: 0 });
    expect(run(save("bulk"), settings).saved).toEqual({ bulk: 1, item: 0, supplier: 0, policy: 0, settings: 1, receipt: 0, auto: 0 });
    const failed = run([{ type: "requested", seq: 1, kind: "save", form: "bulk" }, { type: "failed", seq: 1, message: "x" }], base);
    expect(failed.saved).toEqual(base.saved);
    const suggested = run([{ type: "requested", seq: 1, kind: "suggest", form: "policy" }, { type: "loaded", seq: 1, view: view("a") }], base);
    expect(suggested.saved).toEqual(base.saved);
    const closed = run([{ type: "requested", seq: 1, kind: "close" }, { type: "closed", seq: 1, result: result("n") }], base);
    expect(closed.saved).toEqual(base.saved);
  });
  it("입고·자동 주문 저장도 양식별 횟수를 센다", () => {
    const save = (form: "receipt" | "auto") => [
      { type: "requested", seq: 1, kind: "save", form } as const,
      { type: "loaded", seq: 1, view: view("a") } as const,
    ];
    const receipt = run(save("receipt"));
    expect(receipt.saved.receipt).toBe(1);
    expect(receipt.saved.auto).toBe(0);
    expect(run(save("auto"), receipt).saved).toMatchObject({ receipt: 1, auto: 1 });
  });
  it("마감 날짜는 초기값에서 시작하고 바꾸면 검사·결과를 비우되 저장 뒤에도 남는다", () => {
    const s = run([
      { type: "closeDateChanged", date: "2026-11-01" },
      { type: "requested", seq: 1, kind: "close" },
      { type: "closed", seq: 1, result: result("n") },
    ], initialInventoryState("2026-11-08"));
    expect(initialInventoryState("2026-11-08").close.date).toBe("2026-11-08");
    expect(s.close.date).toBe("2026-11-01");
    expect(run([{ type: "closeReset" }], s).close.date).toBe("2026-11-01");
    expect(run([{ type: "closeDateChanged", date: "2026-11-02" }], s).close.result).toBeNull();
  });
});

describe("inventoryReducer 저장하지 않은 입력", () => {
  it("양식 저장이 성공하면 그 양식의 입력만 저장된 것으로 본다", () => {
    const s = run([
      { type: "edited", form: "bulk" },
      { type: "edited", form: "settings" },
      { type: "requested", seq: 1, kind: "save", form: "settings" },
      { type: "loaded", seq: 1, view: view("a") },
    ]);
    expect(s.edited).toEqual(["bulk"]);
    expect(hasUnsaved(s)).toBe(true);
    const bulk = run([{ type: "requested", seq: 2, kind: "save", form: "bulk" }, { type: "loaded", seq: 2, view: view("b") }], s);
    expect(hasUnsaved(bulk)).toBe(false);
  });

  it("마감 입력이 남아 있으면 품목 저장 뒤에도 저장하지 않은 입력이 있다", () => {
    const s = run([
      { type: "countChanged", itemId: "a", text: "3" },
      { type: "requested", seq: 1, kind: "save", form: "policy" },
      { type: "loaded", seq: 1, view: view("a") },
    ]);
    expect(hasUnsaved(s)).toBe(true);
  });

  it("마감 날짜만 바꿔도 저장하지 않은 입력이다", () => {
    expect(hasUnsaved(run([{ type: "closeDateChanged", date: "2026-11-01" }]))).toBe(true);
  });

  it("불러오기·실패한 저장은 입력을 지우지 않는다", () => {
    const loaded = run([{ type: "edited", form: "item" }, { type: "requested", seq: 1, kind: "load" }, { type: "loaded", seq: 1, view: view("a") }]);
    expect(loaded.edited).toEqual(["item"]);
    const failed = run([{ type: "edited", form: "item" }, { type: "requested", seq: 1, kind: "save", form: "item" }, { type: "failed", seq: 1, message: "x" }]);
    expect(failed.edited).toEqual(["item"]);
  });

  it("같은 양식을 여러 번 고쳐도 한 번만 남는다", () => {
    expect(run([{ type: "edited", form: "item" }, { type: "edited", form: "item" }]).edited).toEqual(["item"]);
  });

  it("버리기(discarded)는 마감 입력과 양식 입력을 모두 비우고 날짜는 둔다", () => {
    const s = run([
      { type: "closeDateChanged", date: "2026-11-01" },
      { type: "countChanged", itemId: "a", text: "3" },
      { type: "edited", form: "bulk" },
      { type: "discarded" },
    ]);
    expect(hasUnsaved(s)).toBe(false);
    expect(s.close.counts).toEqual({});
    expect(s.close.date).toBe("2026-11-01");
  });

  it("새 검사 결과가 오면 이상 수량으로 남은 품목의 조정만 남긴다", () => {
    const flagged = { anomalies: [{ item_id: "a", kind: "drop", previous: "10", counted: "1" }] } as unknown as CloseCheckView;
    const s = run([
      { type: "adjustmentChanged", itemId: "a", delta: "-1", reason: "파손" },
      { type: "adjustmentChanged", itemId: "b", delta: "2", reason: "" },
      { type: "requested", seq: 1, kind: "check" },
      { type: "checked", seq: 1, check: flagged },
    ]);
    expect(s.close.adjustments).toEqual({ a: { delta: "-1", reason: "파손" } });
  });

  it("마감 저장을 기다리는 중에 입력을 버려도 저장 응답은 받는다(서버는 이미 기록했다)", () => {
    const s = run([
      { type: "countChanged", itemId: "a", text: "3" },
      { type: "requested", seq: 1, kind: "close" },
      { type: "discarded" },
      { type: "closed", seq: 1, result: result("new") },
    ]);
    expect(s.view).toEqual(view("new"));
    expect(s.inflight).toBeNull();
  });

  it("마감 입력을 비우거나 버린 뒤 늦게 온 검사 응답은 받지 않는다", () => {
    for (const drop of [{ type: "closeReset" }, { type: "discarded" }] as const) {
      const checked = run([
        { type: "countChanged", itemId: "a", text: "3" },
        { type: "requested", seq: 1, kind: "check" },
        drop,
        { type: "checked", seq: 1, check },
      ]);
      expect(checked.close.check).toBeNull();
      expect(checked.inflight).toBeNull();
    }
  });

  it("마감 입력을 버려도 기다리는 양식 저장은 그대로 받는다", () => {
    const s = run([
      { type: "requested", seq: 1, kind: "save", form: "bulk" },
      { type: "discarded" },
      { type: "loaded", seq: 1, view: view("a") },
    ]);
    expect(s.view).toEqual(view("a"));
    expect(s.saved.bulk).toBe(1);
  });
});

describe("inventoryReducer 주문 초안", () => {
  const draft: OrderDraft = {
    requestId: "manual:1",
    supplierId: "sup_1",
    lines: [
      { itemId: "a", quantity: "3", unitPrice: "100" },
      { itemId: "b", quantity: "5", unitPrice: "200" },
    ],
    repriced: false,
  };
  const order = (status: string) => ({ order_id: "ord_1", status }) as unknown as Order;
  const viewWithHolds = (holds: unknown[]) => ({ holds }) as unknown as InventoryView;
  const opened = () => run([{ type: "orderOpened", draft }]);

  it("주문이 실패하면 초안과 request_id를 두고, 결과를 모르는 그 번호를 거래처별로 기억한다", () => {
    const failed = run([{ type: "requested", seq: 1, kind: "order" }, { type: "failed", seq: 1, message: "연결 실패" }], opened());
    expect(failed.order).toEqual(draft);
    expect(failed.pendingOrderIds).toEqual({ sup_1: "manual:1" });
    expect(run([{ type: "orderCancelled" }], failed).pendingOrderIds).toEqual({ sup_1: "manual:1" }); // 취소해도 남는다
    const done = run(
      [{ type: "requested", seq: 2, kind: "order" }, { type: "ordered", seq: 2, order: { ...order("accepted"), supplier_id: "sup_1" } as Order, view: viewWithHolds([]) }],
      failed,
    );
    expect(done.pendingOrderIds).toEqual({}); // 응답을 받았으면 잊는다
    expect(initialInventoryState().pendingOrderIds).toEqual({});
  });

  it("초안을 열면 이전 안내를 지운다", () => {
    const s = run([{ type: "orderOpened", draft }], { ...initialInventoryState(), orderResult: { status: "accepted", holdReason: null } });
    expect(s.order).toEqual(draft);
    expect(s.orderResult).toBeNull();
    expect(initialInventoryState().order).toBeNull();
    expect(initialInventoryState().orderResult).toBeNull();
  });
  it("수량은 그 줄만 바꾼다", () => {
    const s = run([{ type: "orderQuantityChanged", itemId: "b", quantity: "9" }], opened());
    expect(s.order?.lines).toEqual([
      { itemId: "a", quantity: "3", unitPrice: "100" },
      { itemId: "b", quantity: "9", unitPrice: "200" },
    ]);
  });
  it("줄을 빼고 마지막 줄이면 초안을 닫는다", () => {
    const one = run([{ type: "orderLineRemoved", itemId: "a" }], opened());
    expect(one.order?.lines.map((l) => l.itemId)).toEqual(["b"]);
    expect(run([{ type: "orderLineRemoved", itemId: "b" }], one).order).toBeNull();
  });
  it("초안이 없을 때 수량·줄 빼기는 무시한다", () => {
    const s = initialInventoryState();
    expect(run([{ type: "orderQuantityChanged", itemId: "a", quantity: "1" }], s)).toEqual(s);
    expect(run([{ type: "orderLineRemoved", itemId: "a" }], s)).toEqual(s);
  });
  it("ordered는 현재 요청이면 재고를 바꾸고 초안을 닫고 보류 사유를 안내에 싣는다", () => {
    const hold = { order_id: "ord_1", reason: "out_of_stock" };
    const s = run(
      [
        { type: "requested", seq: 1, kind: "order" },
        { type: "ordered", seq: 1, order: order("rejected"), view: viewWithHolds([{ order_id: "x", reason: "price_changed" }, hold]) },
      ],
      opened(),
    );
    expect(s.order).toBeNull();
    expect(s.inflight).toBeNull();
    expect(s.orderResult).toEqual({ status: "rejected", holdReason: "out_of_stock" });
    expect(s.view).toEqual(viewWithHolds([{ order_id: "x", reason: "price_changed" }, hold]));
    const accepted = run([{ type: "requested", seq: 1, kind: "order" }, { type: "ordered", seq: 1, order: order("accepted"), view: viewWithHolds([]) }], opened());
    expect(accepted.orderResult).toEqual({ status: "accepted", holdReason: null });
  });
  it("늦은 ordered는 버린다", () => {
    const s = run([{ type: "requested", seq: 2, kind: "order" }, { type: "ordered", seq: 1, order: order("accepted"), view: viewWithHolds([]) }], opened());
    expect(s.order).toEqual(draft);
    expect(s.view).toBeNull();
    expect(s.inflight?.seq).toBe(2);
  });
  it("취소해도 기다리던 ordered는 받는다", () => {
    const s = run(
      [
        { type: "requested", seq: 1, kind: "order" },
        { type: "orderCancelled" },
        { type: "ordered", seq: 1, order: order("unknown"), view: viewWithHolds([]) },
      ],
      opened(),
    );
    expect(s.order).toBeNull();
    expect(s.orderResult).toEqual({ status: "unknown", holdReason: null });
    expect(s.view).not.toBeNull();
  });
  it("안내를 닫는다", () => {
    const s = run([{ type: "orderResultClosed" }], { ...initialInventoryState(), orderResult: { status: "accepted", holdReason: null } });
    expect(s.orderResult).toBeNull();
  });
  it("discarded·closeReset은 초안을 건드리지 않는다", () => {
    expect(run([{ type: "discarded" }], opened()).order).toEqual(draft);
    expect(run([{ type: "closeReset" }], opened()).order).toEqual(draft);
  });
});
