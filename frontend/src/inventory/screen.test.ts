import { describe, expect, it } from "vitest";

import { INVENTORY } from "../preview/fixtures";
import { inventoryScreen } from "./screen";
import { initialInventoryState } from "./state";

describe("inventoryScreen", () => {
  it("불러오기 전·실패", () => {
    expect(inventoryScreen(initialInventoryState(), "stock")).toEqual({ kind: "loading" });
    expect(inventoryScreen({ ...initialInventoryState(), loadFailed: true }, "stock")).toEqual({ kind: "unavailable" });
  });

  it("탭마다 맞는 모델", () => {
    const state = { ...initialInventoryState("2026-11-08"), view: INVENTORY };
    expect(inventoryScreen(state, "stock").kind).toBe("stock");
    expect(inventoryScreen(state, "close").kind).toBe("close");
    expect(inventoryScreen(state, "items").kind).toBe("items");
  });

  it("숨긴 품목만 있으면 hasItems가 거짓", () => {
    const view = { ...INVENTORY, items: INVENTORY.items.map((v) => ({ ...v, item: { ...v.item, archived: true } })) };
    const m = inventoryScreen({ ...initialInventoryState(), view }, "stock");
    expect(m.kind === "stock" && m.hasItems).toBe(false);
  });
});

describe("주문·자동 주문 탭", () => {
  it("모델과 현황의 제안", () => {
    const state = { ...initialInventoryState("2026-11-08"), view: INVENTORY };
    const orders = inventoryScreen(state, "orders");
    expect(orders.kind === "orders" && orders.orders).toEqual([]);
    const auto = inventoryScreen(state, "auto");
    expect(auto.kind === "auto" && auto.items.length).toBe(INVENTORY.items.length);
    const stock = inventoryScreen(state, "stock");
    expect(stock.kind === "stock" && stock.model.proposals).toHaveLength(1);
  });
});
