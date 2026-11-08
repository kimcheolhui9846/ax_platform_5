import { describe, expect, it } from "vitest";
import { autoFormKey, autoOrderRequest, autoOrderStart, bulkDrafts, emptyBulkRow, policyRequest, receiptFormKey, receiptRequest, receiptStart, settingsRequest } from "./forms";
import type { OrderCard } from "./orderModel";
import type { ItemView } from "../api/types";

describe("bulkDrafts", () => {
  it("빈 줄은 건너뛰고 빈 수량은 미입력(null)이다", () => {
    const rows = [{ ...emptyBulkRow(), name: " 원단 ", unit: "m" }, emptyBulkRow()];
    expect(bulkDrafts(rows)).toEqual([
      { name: "원단", option: null, kind: "material", unit: "m", procurement: "purchase", supplier_id: null, quantity: null },
    ]);
  });
  it("거래처·종류만 바꾼 줄도 빈 줄이 아니라서 이름이 없다고 걸린다", () => {
    expect(bulkDrafts([{ ...emptyBulkRow(), supplierId: "s1" }])).toBeNull();
    expect(bulkDrafts([{ ...emptyBulkRow(), kind: "packaging" }])).toBeNull();
  });
  it("쓴 줄에 단위가 없거나 수량이 틀리면 등록할 수 없다", () => {
    expect(bulkDrafts([{ ...emptyBulkRow(), name: "원단" }])).toBeNull();
    expect(bulkDrafts([{ ...emptyBulkRow(), name: "원단", unit: "m", quantity: "-1" }])).toBeNull();
    expect(bulkDrafts([emptyBulkRow()])).toBeNull();
  });
});


describe("policyRequest·settingsRequest", () => {
  it("올바른 입력만 요청이 된다", () => {
    expect(policyRequest({ min: "10", target: "30", unit: "5", lead: "3", price: "1200" })).toEqual({
      min_stock: "10", target_stock: "30", purchase_unit: "5", lead_days: 3, unit_price: "1200",
    });
    expect(policyRequest({ min: "", target: "30", unit: "5", lead: "3", price: "1" })).toBeNull();
    expect(policyRequest({ min: "1", target: "3", unit: "5", lead: "1.5", price: "1" })).toBeNull();
    expect(settingsRequest({ address: " 서울 ", ratio: "0.5", staleDays: "7" })).toEqual({ address: "서울", anomaly_drop_ratio: "0.5", stale_days: 7 });
    expect(settingsRequest({ address: "", ratio: "abc", staleDays: "7" })).toBeNull();
  });
});

const CARD = {
  orderId: "o-1",
  lines: [
    { itemId: "a", remainingRaw: "18", received: "0" },
    { itemId: "b", remainingRaw: "0", received: "4" },
    { itemId: "c", remainingRaw: "2.5", received: "1" },
  ],
} as unknown as OrderCard;

describe("입고 양식", () => {
  it("처음 값은 남은 수량이 있는 줄만, 남은 수량으로, 마감에서 센 것은 아님", () => {
    expect(receiptStart(CARD)).toEqual([
      { itemId: "a", quantity: "18", alreadyCounted: false },
      { itemId: "c", quantity: "2.5", alreadyCounted: false },
    ]);
  });
  it("빈 칸 줄은 보내지 않고 수량은 다듬고 already_counted를 싣는다", () => {
    expect(
      receiptRequest([
        { itemId: "a", quantity: " 3 ", alreadyCounted: true },
        { itemId: "c", quantity: "  ", alreadyCounted: false },
      ]),
    ).toEqual({ lines: [{ item_id: "a", quantity: "3", already_counted: true }] });
  });
  it("모두 비었거나 쓴 줄이 양수가 아니면 null", () => {
    expect(receiptRequest([{ itemId: "a", quantity: "", alreadyCounted: false }])).toBeNull();
    expect(receiptRequest([{ itemId: "a", quantity: "0", alreadyCounted: false }])).toBeNull();
    expect(receiptRequest([{ itemId: "a", quantity: "x", alreadyCounted: false }, { itemId: "c", quantity: "1", alreadyCounted: false }])).toBeNull();
    expect(receiptRequest([])).toBeNull();
  });
  it("저장 횟수나 입고 수량이 바뀌면 key가 바뀐다", () => {
    const next = { ...CARD, lines: [{ ...CARD.lines[0], received: "3" }] } as OrderCard;
    expect(receiptFormKey(0, CARD)).not.toBe(receiptFormKey(1, CARD));
    expect(receiptFormKey(0, CARD)).not.toBe(receiptFormKey(0, next));
  });
});

describe("자동 주문 양식", () => {
  it("설정이 없으면 꺼짐과 시작 한도", () => {
    expect(autoOrderStart(null)).toEqual({ enabled: false, consent: false, perOrder: "100000", monthly: "300000" });
  });
  it("설정이 있으면 그 값이고 동의 기록이 있으면 동의함", () => {
    const setting = { enabled: true, consented_at: "2026-11-01T00:00:00Z", per_order_limit: "1000.50", monthly_limit: "5000" };
    expect(autoOrderStart(setting)).toEqual({ enabled: true, consent: true, perOrder: "1000.50", monthly: "5000" });
    expect(autoOrderStart({ ...setting, consented_at: null }).consent).toBe(false);
  });
  it("요청 본문은 한도를 다듬어 싣는다", () => {
    expect(autoOrderRequest({ enabled: true, consent: true, perOrder: " 100000 ", monthly: "300000.5" })).toEqual({
      enabled: true,
      consent: true,
      per_order_limit: "100000",
      monthly_limit: "300000.5",
    });
  });
  it("켜면서 동의하지 않았거나 한도가 금액 글이 아니면 null, 끄기는 동의 없이도 된다", () => {
    expect(autoOrderRequest({ enabled: true, consent: false, perOrder: "1", monthly: "2" })).toBeNull();
    expect(autoOrderRequest({ enabled: false, consent: false, perOrder: "1", monthly: "2" })).not.toBeNull();
    expect(autoOrderRequest({ enabled: false, consent: false, perOrder: "", monthly: "2" })).toBeNull();
    expect(autoOrderRequest({ enabled: false, consent: false, perOrder: "1", monthly: "2.123" })).toBeNull();
    expect(autoOrderRequest({ enabled: false, consent: false, perOrder: "-1", monthly: "2" })).toBeNull();
  });
  it("저장 횟수·품목·설정이 바뀌면 key가 바뀐다", () => {
    const item = { item: { item_id: "a" }, auto_order: null } as unknown as ItemView;
    expect(autoFormKey(0, item)).not.toBe(autoFormKey(1, item));
    expect(autoFormKey(0, item)).not.toBe(autoFormKey(0, { ...item, auto_order: { enabled: true } } as unknown as ItemView));
  });
});
