import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

import { api } from "./client";
import {
  addItem,
  addItems,
  applySuggestion,
  checkClose,
  getInventory,
  placeOrder,
  receive,
  recordClose,
  resolveHold,
  setPolicy,
  suggestPolicy,
  updateItem,
} from "./inventory";
import type { ItemDraft } from "./types";

const BASE = "/api/v1/inventory";

beforeEach(() => vi.clearAllMocks());

describe("inventory API 래퍼", () => {
  it("재고 묶음 조회", async () => {
    await getInventory();
    expect(api.GET).toHaveBeenCalledWith(BASE);
  });

  it("품목 여러 개 추가는 {items} 본문", async () => {
    const items = [{ name: "원두" }] as unknown as ItemDraft[];
    await addItems(items);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/items/bulk`, { body: { items } });
  });

  it("품목 하나 추가·수정", async () => {
    const item = { name: "우유" } as unknown as ItemDraft;
    await addItem(item);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/items`, { body: item });
    await updateItem("i1", { name: "두유" } as never);
    expect(api.PATCH).toHaveBeenCalledWith(`${BASE}/items/{item_id}`, {
      params: { path: { item_id: "i1" } },
      body: { name: "두유" },
    });
  });

  it("기준 저장은 PUT", async () => {
    const body = { target_days: 3 } as never;
    await setPolicy("i1", body);
    expect(api.PUT).toHaveBeenCalledWith(`${BASE}/items/{item_id}/policy`, {
      params: { path: { item_id: "i1" } },
      body,
    });
  });

  it("마감 확인·기록", async () => {
    const body = { counts: [] } as never;
    await checkClose(body);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/closes/check`, { body });
    await recordClose(body);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/closes`, { body });
  });

  it("AI 기준 추천·적용", async () => {
    await suggestPolicy("i1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/items/{item_id}/policy/suggestion`, {
      params: { path: { item_id: "i1" } },
    });
    await applySuggestion("i1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/items/{item_id}/policy/suggestion/apply`, {
      params: { path: { item_id: "i1" } },
    });
  });

  it("주문·입고·보류 해결", async () => {
    const body = { lines: [] } as never;
    await placeOrder(body);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/orders`, { body });
    await receive("o1", body);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/orders/{order_id}/receipts`, {
      params: { path: { order_id: "o1" } },
      body,
    });
    await resolveHold("h1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/holds/{hold_id}/resolve`, {
      params: { path: { hold_id: "h1" } },
    });
  });
});
