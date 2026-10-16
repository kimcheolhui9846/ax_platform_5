import type { Middleware } from "openapi-fetch";
import { describe, expect, it } from "vitest";

import { BACKEND_UNREACHABLE, CLIENT_ID_HEADER, apiBaseUrl, errorMessage, toOutcome, withClientId } from "./client";

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

  const json = { "content-type": "application/json" };

  it("오류 응답이면 detail 문구로 실패한다", () => {
    const response = new Response(null, { status: 422, headers: json });
    expect(toOutcome({ error: { detail: "요청 형식이 올바르지 않습니다." }, response })).toEqual({
      ok: false,
      message: "요청 형식이 올바르지 않습니다.",
    });
  });

  it("JSON 실패인데 detail 문자열이 없으면 기본 문구를 쓴다", () => {
    const response = new Response(null, { status: 500, headers: json });
    expect(toOutcome({ error: { foo: 1 }, response })).toEqual({ ok: false, message: FALLBACK });
  });

  it("charset이 붙은 JSON도 JSON이다", () => {
    const response = new Response(null, {
      status: 404,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
    expect(toOutcome({ error: { detail: "세션을 찾을 수 없습니다." }, response })).toEqual({
      ok: false,
      message: "세션을 찾을 수 없습니다.",
    });
  });

  it("JSON 없는 게이트웨이 실패는 백엔드 미연결이다", () => {
    const response = new Response(null, { status: 504 });
    expect(toOutcome({ response })).toEqual({ ok: false, message: BACKEND_UNREACHABLE });
  });

  it("버셀 404 HTML은 백엔드 미연결이다", () => {
    const response = new Response(null, {
      status: 404,
      headers: { "content-type": "text/html; charset=utf-8" },
    });
    expect(toOutcome({ error: "<!doctype html><title>404</title>", response })).toEqual({
      ok: false,
      message: BACKEND_UNREACHABLE,
    });
  });
});

describe("apiBaseUrl", () => {
  it("값이 없으면 같은 출처(/)를 쓴다", () => {
    expect(apiBaseUrl(undefined)).toBe("/");
    expect(apiBaseUrl("")).toBe("/");
    expect(apiBaseUrl("   ")).toBe("/");
  });

  it("끝의 슬래시를 하나로 맞춘다", () => {
    expect(apiBaseUrl("https://api.example.com")).toBe("https://api.example.com/");
    expect(apiBaseUrl("https://api.example.com///")).toBe("https://api.example.com/");
  });
});

describe("BACKEND_UNREACHABLE", () => {
  it("미리보기 주소를 안내한다", () => {
    expect(BACKEND_UNREACHABLE).toContain("/preview");
  });
});

describe("withClientId", () => {
  it("요청마다 익명 사용자 ID 헤더를 붙인다", async () => {
    const request = new Request("http://localhost/api/v1/coaching/sessions/sess_1");
    const onRequest = withClientId("client-0001").onRequest!;
    const sent = await onRequest({ request } as Parameters<NonNullable<Middleware["onRequest"]>>[0]);
    expect((sent as Request).headers.get(CLIENT_ID_HEADER)).toBe("client-0001");
  });
});
