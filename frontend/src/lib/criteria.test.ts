import { describe, expect, it } from "vitest";

import { makeSession } from "../testing/factories";
import { criteriaRows } from "./criteria";

describe("criteriaRows", () => {
  it("확인한 값은 출처, AI 가정은 확인 필요, 미정은 마지막에", () => {
    const { summary } = makeSession();
    const rows = criteriaRows(
      [...summary, { ...summary[0], field: "price", label: "가격 방향", value: "1~3만원", is_assumption: true }],
      [{ field: "mvp", label: "MVP 구성" }],
    );
    expect(rows).toEqual([
      { field: "product_idea", label: "상품 아이디어", value: "수제 향초", note: "직접 입력", private: false },
      { field: "price", label: "가격 방향", value: "1~3만원", note: "AI 가정 · 확인 필요", private: false },
      { field: "mvp", label: "MVP 구성", value: "아직 미정", note: null, private: false },
    ]);
  });

  it("AI에 보내지 않기로 한 값은 private로 표시한다", () => {
    const { summary } = makeSession();
    expect(criteriaRows([{ ...summary[0], private: true }], [])[0].private).toBe(true);
  });
});
