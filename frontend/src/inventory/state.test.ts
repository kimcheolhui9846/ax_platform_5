import { describe, expect, it } from "vitest";
import type { CloseCheckView, CloseView, InventoryView } from "../api/types";
import { initialInventoryState, inventoryReducer } from "./state";
import type { InventoryAction, InventoryState } from "./state";

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
    expect(s.dirty).toBe(true);
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
    expect(s.dirty).toBe(true);
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
    expect(s.dirty).toBe(true);
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
    expect(s.dirty).toBe(false);
  });

  it("closeReset은 입력과 결과를 비운다", () => {
    const s = run([{ type: "countChanged", itemId: "a", text: "3" }, { type: "closeReset" }]);
    expect(s.close.counts).toEqual({});
    expect(s.dirty).toBe(false);
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

  it("edited, saved, toastClosed", () => {
    const edited = run([{ type: "edited" }]);
    expect(edited.dirty).toBe(true);
    expect(inventoryReducer(edited, { type: "saved" }).dirty).toBe(false);
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
    const save = (form: "bulk" | "settings") => [
      { type: "requested", seq: 1, kind: "save", form } as const,
      { type: "loaded", seq: 1, view: view("a") } as const,
    ];
    const settings = run(save("settings"), base);
    expect(settings.saved).toEqual({ bulk: 0, item: 0, supplier: 0, policy: 0, settings: 1 });
    expect(run(save("bulk"), settings).saved).toEqual({ bulk: 1, item: 0, supplier: 0, policy: 0, settings: 1 });
    const failed = run([{ type: "requested", seq: 1, kind: "save", form: "bulk" }, { type: "failed", seq: 1, message: "x" }], base);
    expect(failed.saved).toEqual(base.saved);
    const suggested = run([{ type: "requested", seq: 1, kind: "suggest", form: "policy" }, { type: "loaded", seq: 1, view: view("a") }], base);
    expect(suggested.saved).toEqual(base.saved);
    const closed = run([{ type: "requested", seq: 1, kind: "close" }, { type: "closed", seq: 1, result: result("n") }], base);
    expect(closed.saved).toEqual(base.saved);
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
