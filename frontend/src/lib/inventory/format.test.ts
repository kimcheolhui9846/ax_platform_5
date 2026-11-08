import { describe, expect, it } from "vitest";
import { ANOMALY_LABELS, KIND_LABELS, lineAmount, moneyText, ORIGIN_LABELS, PROCUREMENT_LABELS, quantityText, remainingQuantity, STATUS_LABELS, sumAmounts } from "./format";

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
    expect(moneyText("4500.00")).toBe("4,500원"); // 소수가 모두 0이면 뺀다
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

describe("lineAmount·sumAmounts·remainingQuantity", () => {
  it("수량 × 단가를 0.01로 반올림(절반 올림)한다", () => {
    expect(lineAmount("10", "1250")).toBe("12500.00");
    expect(lineAmount("0.5", "0.01")).toBe("0.01"); // 0.005 -> 0.01
    expect(lineAmount("0.1", "0.2")).toBe("0.02"); // 부동소수 오차 없음
    expect(lineAmount("2.5", "4500.00")).toBe("11250.00");
    expect(lineAmount("0.001", "1")).toBe("0.00");
  });
  it("숫자 글이 아니면 null", () => {
    expect(lineAmount("", "100")).toBeNull();
    expect(lineAmount("abc", "100")).toBeNull();
    expect(lineAmount("1", "x")).toBeNull();
  });
  it("센트 합", () => {
    expect(sumAmounts(["0.10", "0.20"])).toBe("0.30");
    expect(sumAmounts([])).toBe("0.00");
    expect(sumAmounts(["12500.00", "11250.00"])).toBe("23750.00");
  });
  it("남은 수량은 두 값의 차(0 아래로 내려가지 않는다)", () => {
    expect(remainingQuantity("10.00", "4.50")).toBe("5.5");
    expect(remainingQuantity("10", "10")).toBe("0");
    expect(remainingQuantity("3", "5")).toBe("0");
  });
  it("출처 라벨", () => {
    expect(ORIGIN_LABELS).toEqual({ manual: "직접 주문", auto: "자동 주문" });
  });
});
