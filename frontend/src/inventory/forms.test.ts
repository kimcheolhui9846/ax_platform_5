import { describe, expect, it } from "vitest";
import { bulkDrafts, emptyBulkRow, policyRequest, settingsRequest } from "./forms";

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
