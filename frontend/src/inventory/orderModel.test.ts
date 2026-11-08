import { describe, expect, it } from "vitest";

import type { Hold, InventoryView, ItemView, Order } from "../api/types";
import { INVENTORY } from "../preview/fixtures";
import { autoModel, autoRows, draftFromHold, draftFromProposal, holdRows, orderCards, orderConfirmModel, orderProposals, orderResultText } from "./orderModel";

const base = INVENTORY.items;
const flour = base[0]; // it-1 부족, 제안 40, 거래처 sup-1(픽스처 확인)
const withItems = (items: ItemView[], patch: Partial<InventoryView> = {}): InventoryView => ({ ...INVENTORY, items, ...patch });
const order = (patch: Partial<Order> = {}): Order => ({
  order_id: "o-1",
  request_id: "r-1",
  supplier_id: "sup-1",
  lines: [{ item_id: "it-1", quantity: "40", unit_price: "4500", received: "0" }],
  total: "180000.00",
  origin: "manual",
  status: "accepted",
  reject_reason: null,
  current_prices: {},
  supplier_ref: null,
  created_at: "2026-11-08T03:00:00Z",
  updated_at: "2026-11-08T03:00:00Z",
  ...patch,
});
const hold = (patch: Partial<Hold> = {}): Hold => ({
  hold_id: "h-1",
  item_id: "it-1",
  order_id: "o-1",
  reason: "price_changed",
  current_unit_price: "5000",
  created_at: "2026-11-08T03:00:00Z",
  resolved: false,
  ...patch,
});

describe("orderProposals", () => {
  it("부족한 구매 품목을 거래처별로 묶는다", () => {
    const groups = orderProposals(INVENTORY);
    expect(groups).toHaveLength(1);
    expect(groups[0].supplierId).toBe(flour.item.supplier_id);
    expect(groups[0].lines[0]).toMatchObject({ itemId: "it-1", suggested: "40", unitPrice: "4500" });
  });
  it("거래처 이름순, 품목 이름순", () => {
    const mk = (id: string, name: string, supplier: string): ItemView => ({
      ...flour,
      item: { ...flour.item, item_id: id, name, supplier_id: supplier },
    });
    const view = withItems([mk("a", "나", "sup-2"), mk("b", "다", "sup-1"), mk("c", "가", "sup-1")]);
    const groups = orderProposals(view);
    expect(groups.map((g) => g.supplierName)).toEqual(["새벽 포장", "한빛 식자재"]);
    expect(groups[1].lines.map((l) => l.name)).toEqual(["가", "다"]);
  });
  it("거래처 없음·숨김·제작·기준 없음·부족 아님은 뺀다", () => {
    const v = (patch: Partial<ItemView>, ip: Partial<ItemView["item"]> = {}): ItemView => ({ ...flour, ...patch, item: { ...flour.item, ...ip } });
    const view = withItems([
      v({}, { supplier_id: null }),
      v({}, { archived: true }),
      v({}, { procurement: "make" }),
      v({ policy: null }),
      v({ status: "ok" }),
      v({ suggested_quantity: null }),
    ]);
    expect(orderProposals(view)).toEqual([]);
  });
});

describe("초안", () => {
  it("제안에서 연 초안은 repriced가 거짓", () => {
    const group = orderProposals(INVENTORY)[0];
    expect(draftFromProposal(group, "manual:1")).toEqual({
      requestId: "manual:1",
      supplierId: group.supplierId,
      lines: [{ itemId: "it-1", quantity: "40", unitPrice: "4500" }],
      repriced: false,
    });
  });
  it("보류에서 연 초안은 새 단가와 보류 주문의 수량", () => {
    const view = withItems(base, { orders: [order({ lines: [{ item_id: "it-1", quantity: "30", unit_price: "4500", received: "0" }] })], holds: [hold()] });
    expect(draftFromHold(view, "h-1", "manual:2")).toEqual({
      requestId: "manual:2",
      supplierId: "sup-1",
      lines: [{ itemId: "it-1", quantity: "30", unitPrice: "5000" }],
      repriced: true,
    });
  });
  it("주문이 없으면 제안량, 그것도 없으면 null", () => {
    const view = withItems(base, { holds: [hold({ order_id: null })] });
    expect(draftFromHold(view, "h-1", "x")?.lines[0].quantity).toBe("40");
    const noSuggest = withItems([{ ...flour, suggested_quantity: null }, ...base.slice(1)], { holds: [hold({ order_id: null })] });
    expect(draftFromHold(noSuggest, "h-1", "x")).toBeNull();
  });
  it("가격 변동이 아니거나 새 단가가 없거나 주문 불가 품목이면 null", () => {
    expect(draftFromHold(withItems(base, { holds: [hold({ reason: "out_of_stock" })] }), "h-1", "x")).toBeNull();
    expect(draftFromHold(withItems(base, { holds: [hold({ current_unit_price: null })] }), "h-1", "x")).toBeNull();
    expect(draftFromHold(withItems(base, { holds: [hold({ item_id: "it-5" })] }), "h-1", "x")).toBeNull();
    expect(draftFromHold(withItems(base, { holds: [hold()] }), "nope", "x")).toBeNull();
  });
});

describe("orderConfirmModel", () => {
  const draft = { requestId: "r", supplierId: "sup-1", lines: [{ itemId: "it-1", quantity: "10", unitPrice: "1250" }], repriced: false };
  it("줄 금액과 총액, 제출 가능", () => {
    const m = orderConfirmModel(INVENTORY, draft);
    expect(m.supplierName).toBe("한빛 식자재");
    expect(m.address).toBe("서울시 마포구 월드컵로 1");
    expect(m.lines[0]).toMatchObject({ itemId: "it-1", quantity: "10", unitPriceText: "1,250원", amountText: "12,500원", valid: true });
    expect(m.totalText).toBe("12,500원");
    expect(m.canSubmit).toBe(true);
  });
  it("수량이 비었거나 0이면 valid가 거짓이고 제출 불가, 총액에서 빠진다", () => {
    const m = orderConfirmModel(INVENTORY, {
      ...draft,
      lines: [...draft.lines, { itemId: "it-4", quantity: "0", unitPrice: "100" }, { itemId: "it-2", quantity: "", unitPrice: "100" }],
    });
    expect(m.lines.map((l) => l.valid)).toEqual([true, false, false]);
    expect(m.lines[2].amountText).toBe("-");
    expect(m.totalText).toBe("12,500원");
    expect(m.canSubmit).toBe(false);
  });
  it("줄이 없거나 배송지가 없으면 제출 불가", () => {
    expect(orderConfirmModel(INVENTORY, { ...draft, lines: [] }).canSubmit).toBe(false);
    const m = orderConfirmModel({ ...INVENTORY, settings: { ...INVENTORY.settings, address: "  " } }, draft);
    expect(m.addressMissing).toBe(true);
    expect(m.canSubmit).toBe(false);
  });
  it("보류의 새 단가로 연 초안 표시", () => {
    expect(orderConfirmModel(INVENTORY, { ...draft, repriced: true }).repriced).toBe(true);
  });
});

describe("orderResultText", () => {
  it("상태별 문구", () => {
    expect(orderResultText({ status: "accepted", holdReason: null })).toBe("주문이 접수됐어요");
    expect(orderResultText({ status: "rejected", holdReason: "out_of_stock" })).toBe("주문이 거절됐어요: 거래처 재고가 없어요");
    expect(orderResultText({ status: "rejected", holdReason: null })).toBe("주문이 거절됐어요");
    expect(orderResultText({ status: "unknown", holdReason: null })).toBe("접수 여부를 확인하지 못했어요. 주문·입고 탭에서 다시 확인해 주세요");
  });
});

describe("orderCards", () => {
  it("남은 수량과 버튼", () => {
    const view = withItems(base, {
      orders: [
        order({ status: "partially_received", lines: [{ item_id: "it-1", quantity: "40.00", unit_price: "4500", received: "15.50" }] }),
        order({ order_id: "o-2", status: "unknown", origin: "auto" }),
        order({ order_id: "o-3", status: "received", lines: [{ item_id: "it-1", quantity: "40", unit_price: "4500", received: "40" }] }),
      ],
    });
    const cards = orderCards(view);
    expect(cards.map((c) => c.orderId)).toEqual(["o-1", "o-2", "o-3"]);
    expect(cards[0]).toMatchObject({ supplierName: "한빛 식자재", originLabel: "직접 주문", statusLabel: "일부 입고", canReceive: true, canRefresh: false, createdDate: "2026-11-08" });
    expect(cards[0].lines[0]).toMatchObject({ name: "국산 밀가루", ordered: "40 kg", received: "15.5 kg", remaining: "24.5 kg", remainingRaw: "24.5" });
    expect(cards[1]).toMatchObject({ originLabel: "자동 주문", canRefresh: true, canReceive: false });
    expect(cards[2].lines[0]).toMatchObject({ remaining: "0 kg", remainingRaw: "0" });
    expect(cards[2].canReceive).toBe(false);
  });
});

describe("holdRows", () => {
  it("해결된 보류는 뺀다, 버튼과 새 단가", () => {
    const view = withItems(base, {
      orders: [order({ status: "unknown" })],
      holds: [hold(), hold({ hold_id: "h-2", resolved: true }), hold({ hold_id: "h-3", reason: "unknown", current_unit_price: null })],
    });
    const rows = holdRows(view);
    expect(rows.map((r) => r.holdId)).toEqual(["h-1", "h-3"]);
    expect(rows[0]).toMatchObject({ itemName: "국산 밀가루", reasonLabel: "가격이 바뀌었어요", priceText: "5,000원", canReview: true, canRefresh: true, orderId: "o-1" });
    expect(rows[1]).toMatchObject({ canReview: false, priceText: null });
  });
});

describe("자동 주문", () => {
  const auto = (patch = {}) => ({ enabled: true, consented_at: "2026-11-01T00:00:00Z", per_order_limit: "200000", monthly_limit: "1000000", ...patch });
  it("숨긴·제작 품목은 빼고, 거래처·기준 없으면 orderable 거짓", () => {
    const noPolicy: ItemView = { ...base[3], policy: null, item: { ...base[3].item, item_id: "it-x", name: "기준 없음" } };
    const rows = autoRows(withItems([...base, noPolicy]));
    expect(rows.map((r) => r.itemId)).toEqual(["it-1", "it-2", "it-3", "it-4", "it-x"]);
    expect(rows.find((r) => r.itemId === "it-x")).toMatchObject({ orderable: false, reason: "거래처와 보충 기준이 필요해요" });
    expect(rows[0]).toMatchObject({ orderable: true, reason: "", enabled: false, lastResult: "아직 없음" });
  });
  it("한도 글과 마지막 결과", () => {
    const items = [{ ...base[0], auto_order: auto() }, ...base.slice(1)];
    const view = withItems(items, {
      orders: [
        order({ order_id: "o-a", origin: "auto", status: "accepted", created_at: "2026-11-05T03:00:00Z" }),
        order({ order_id: "o-b", origin: "auto", status: "rejected", created_at: "2026-11-07T03:00:00Z" }),
        order({ order_id: "o-m", origin: "manual", status: "accepted", created_at: "2026-11-08T03:00:00Z" }),
      ],
    });
    const row = autoRows(view)[0];
    expect(row.enabled).toBe(true);
    expect(row.limitsText).toBe("1회 200,000원 · 월 1,000,000원");
    expect(row.lastResult).toBe("주문 거절 · 2026-11-07");
  });
  it("더 최근의 미해결 자동 보류는 그 사유", () => {
    const view = withItems(base, {
      orders: [order({ origin: "auto", created_at: "2026-11-05T03:00:00Z" })],
      holds: [hold({ order_id: null, reason: "stale_count", created_at: "2026-11-07T03:00:00Z" }), hold({ hold_id: "h-r", order_id: null, resolved: true, created_at: "2026-11-09T03:00:00Z" })],
    });
    expect(autoRows(view)[0].lastResult).toBe("재고 확인이 오래됐어요 · 2026-11-07");
  });
  it("모델은 배송지 없음을 알린다", () => {
    expect(autoModel(INVENTORY).addressMissing).toBe(false);
    expect(autoModel({ ...INVENTORY, settings: { ...INVENTORY.settings, address: "" } }).addressMissing).toBe(true);
  });
});
