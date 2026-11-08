import { describe, expect, it } from "vitest";
import { ANOMALY_LABELS, KIND_LABELS, moneyText, PROCUREMENT_LABELS, quantityText, STATUS_LABELS } from "./format";

describe("quantityText", () => {
  it("미입력은 0이 아니라 '미입력'", () => {
    expect(quantityText(null, "m")).toBe("미입력");
    expect(quantityText("0", "m")).toBe("0 m");
  });
  it("천 단위 쉼표, 소수 끝의 0은 뺀다(서버가 붙인 자리 맞춤)", () => {
    expect(quantityText("1234.5", "m")).toBe("1,234.5 m");
    expect(quantityText("1234567", "개")).toBe("1,234,567 개");
    expect(quantityText("10.50", "kg")).toBe("10.5 kg");
    expect(quantityText("30.00", "L")).toBe("30 L");
    expect(quantityText("100", "L")).toBe("100 L");
    expect(quantityText("-1500", "개")).toBe("-1,500 개");
  });
});

describe("moneyText", () => {
  it("원 단위와 쉼표", () => {
    expect(moneyText("12000")).toBe("12,000원");
    expect(moneyText("1200.50")).toBe("1,200.50원");
  });
});

describe("라벨", () => {
  it("한국어 라벨이 있다", () => {
    expect(KIND_LABELS.finished).toBe("완제품");
    expect(STATUS_LABELS.in_transit).toBe("배송 중");
    expect(PROCUREMENT_LABELS.make).toBe("직접 제작");
    expect(ANOMALY_LABELS.drop).toBeTruthy();
    expect(ANOMALY_LABELS.increase).toBeTruthy();
  });
});
