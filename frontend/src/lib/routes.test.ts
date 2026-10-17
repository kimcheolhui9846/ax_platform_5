import { describe, expect, it } from "vitest";

import { HOME, contextOf, isRouteHash, parseRoute, sessionIdOf, taskOf, toHash } from "./routes";
import type { Route } from "./routes";

const ROUTES: [Route, string][] = [
  [{ name: "home" }, "#/"],
  [{ name: "guide" }, "#/guide"],
  [{ name: "request", task: "product_planning" }, "#/product_planning/request"],
  [{ name: "mode", task: "product_planning" }, "#/product_planning/mode"],
  [{ name: "question", sessionId: "sess_1" }, "#/s/sess_1/question"],
  [{ name: "revise", sessionId: "sess_1", questionId: "q_1" }, "#/s/sess_1/question/q_1"],
  [{ name: "confirm", sessionId: "sess_1" }, "#/s/sess_1/confirm"],
  [{ name: "result", sessionId: "sess_1" }, "#/s/sess_1/result"],
];

describe("parseRoute·toHash", () => {
  it.each(ROUTES)("%o ↔ %s", (route, hash) => {
    expect(toHash(route)).toBe(hash);
    expect(parseRoute(hash)).toEqual(route);
  });

  it("빈 주소와 모르는 주소는 홈이다", () => {
    for (const hash of ["", "#", "#/", "#/nope", "#/s/sess_1", "#/s/sess_1/edit", "#/product_planning/question", "#/a/b/c/d/e"]) {
      expect(parseRoute(hash)).toEqual(HOME);
    }
  });

  it("주소에 넣는 값은 인코딩한다", () => {
    const route: Route = { name: "question", sessionId: "세션 1" };
    expect(toHash(route)).toBe("#/s/%EC%84%B8%EC%85%98%201/question");
    expect(parseRoute(toHash(route))).toEqual(route);
  });

  it("잘못 인코딩된 조각은 그대로 둔다", () => {
    expect(parseRoute("#/s/%E0%A4%A/question")).toEqual({ name: "question", sessionId: "%E0%A4%A" });
  });
});

describe("contextOf", () => {
  it("요청·모드는 같은 과제 묶음, 세션 화면은 같은 세션 묶음이다", () => {
    expect(contextOf({ name: "request", task: "a" })).toBe(contextOf({ name: "mode", task: "a" }));
    expect(contextOf({ name: "question", sessionId: "s" })).toBe(contextOf({ name: "result", sessionId: "s" }));
    expect(contextOf({ name: "revise", sessionId: "s", questionId: "q" })).toBe(contextOf({ name: "confirm", sessionId: "s" }));
  });

  it("다른 과제·세션·공용 화면은 다른 묶음이다", () => {
    expect(contextOf({ name: "request", task: "a" })).not.toBe(contextOf({ name: "request", task: "b" }));
    expect(contextOf({ name: "question", sessionId: "s" })).not.toBe(contextOf({ name: "question", sessionId: "t" }));
    expect(contextOf(HOME)).not.toBe(contextOf({ name: "guide" }));
  });
});

describe("taskOf·sessionIdOf", () => {
  it("과제 화면은 과제, 세션 화면은 세션 id를 가진다", () => {
    expect(taskOf({ name: "mode", task: "branding" })).toBe("branding");
    expect(taskOf({ name: "question", sessionId: "s" })).toBeNull();
    expect(sessionIdOf({ name: "revise", sessionId: "s", questionId: "q" })).toBe("s");
    expect(sessionIdOf(HOME)).toBeNull();
  });
});

describe("isRouteHash", () => {
  it("화면 주소(#/…)와 빈 주소만 화면 이동이다. 문서 안 앵커(#main)는 아니다", () => {
    for (const hash of ["", "#", "#/", "#/guide", "#/s/sess_1/question"]) expect(isRouteHash(hash)).toBe(true);
    for (const hash of ["#main", "#question-desktop-main"]) expect(isRouteHash(hash)).toBe(false);
  });
});
