import { describe, expect, it } from "vitest";

import { errorMessage } from "./client";

const FALLBACK = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";

describe("errorMessage", () => {
  it("detail이 문자열이면 그대로 돌려준다", () => {
    expect(errorMessage({ detail: "세션을 찾을 수 없습니다." })).toBe("세션을 찾을 수 없습니다.");
  });

  it("detail이 문자열이 아니면 기본 문구를 쓴다", () => {
    expect(errorMessage({ detail: [{ msg: "x" }] })).toBe(FALLBACK);
  });

  it("객체가 아니면 기본 문구를 쓴다", () => {
    expect(errorMessage(undefined)).toBe(FALLBACK);
    expect(errorMessage(null)).toBe(FALLBACK);
    expect(errorMessage("oops")).toBe(FALLBACK);
  });
});
