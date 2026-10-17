import { describe, expect, it } from "vitest";

import { documentSections, resultKicker, resultTitle } from "./document";

describe("결과 문서", () => {
  it("카드를 순서대로 01, 02 … 섹션으로", () => {
    const sections = documentSections([
      { card_type: "action", order: 3, title: "다음 실행", body: "다섯 명에게 묻기" },
      { card_type: "diagnosis", order: 1, title: "상품 콘셉트", body: "한글 파우치" },
    ]);
    expect(sections).toEqual([
      { key: "diagnosis-1", number: "01", heading: "상품 콘셉트", tag: "진단", body: "한글 파우치" },
      { key: "action-3", number: "02", heading: "다음 실행", tag: "실행 과제", body: "다섯 명에게 묻기" },
    ]);
  });

  it("제목과 위 작은 줄", () => {
    expect(resultTitle("상품기획")).toBe("상품기획 초안");
    expect(resultKicker("상품 콘셉트 · 첫 제작 기획서", false)).toBe("상품 콘셉트 · 첫 제작 기획서");
    expect(resultKicker("상품 콘셉트 · 첫 제작 기획서", true)).toBe("상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });
});
