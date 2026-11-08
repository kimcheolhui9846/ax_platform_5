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
