import { describe, expect, it } from "vitest";

import { errorMessage, toOutcome } from "./client";

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

describe("toOutcome", () => {
  const ok = new Response(null, { status: 200 });

  it("오류가 없으면 본문이 비어 있어도 성공이다", () => {
    expect(toOutcome({ data: undefined, error: undefined, response: ok })).toEqual({ ok: true, data: undefined });
    expect(toOutcome({ data: { a: 1 }, response: ok })).toEqual({ ok: true, data: { a: 1 } });
  });

  it("오류 응답이면 detail 문구로 실패한다", () => {
    const response = new Response(null, { status: 422 });
    expect(toOutcome({ error: { detail: "요청 형식이 올바르지 않습니다." }, response })).toEqual({
      ok: false,
      message: "요청 형식이 올바르지 않습니다.",
    });
  });

  it("상태가 실패면 오류 본문이 없어도 실패한다", () => {
    const response = new Response(null, { status: 504 });
    expect(toOutcome({ response })).toEqual({ ok: false, message: FALLBACK });
  });
});
