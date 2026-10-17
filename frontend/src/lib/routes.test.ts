import { describe, expect, it } from "vitest";

import { HOME, contextOf, isListRoute, isRouteHash, parseRoute, sessionIdOf, taskOf, toHash } from "./routes";
import type { Route } from "./routes";

const ROUTES: [Route, string][] = [
  [{ name: "home" }, "#/"],
  [{ name: "guide" }, "#/guide"],
  [{ name: "request", task: "product_planning" }, "#/product_planning/request"],
  [{ name: "mode", task: "product_planning" }, "#/product_planning/mode"],
  [{ name: "question", sessionId: "sess_1" }, "#/s/sess_1/question"],
  [{ name: "revise", sessionId: "sess_1", questionId: "q_1" }, "#/s/sess_1/question/q_1"],
  [{ name: "confirm", sessionId: "sess_1" }, "#/s/sess_1/confirm"],
  [{ name: "failed", sessionId: "sess_1" }, "#/s/sess_1/failed"],
  [{ name: "result", sessionId: "sess_1" }, "#/s/sess_1/result"],
  [{ name: "evidence", sessionId: "sess_1" }, "#/s/sess_1/evidence"],
  [{ name: "work" }, "#/work"],
  [{ name: "documents" }, "#/documents"],
  [{ name: "saved", sessionId: "sess_1", version: 2 }, "#/s/sess_1/saved/2"],
  [{ name: "version", sessionId: "sess_1", version: 2 }, "#/s/sess_1/v/2"],
];

describe("parseRoute·toHash", () => {
  it.each(ROUTES)("%o ↔ %s", (route, hash) => {
    expect(toHash(route)).toBe(hash);
    expect(parseRoute(hash)).toEqual(route);
  });

  it("빈 주소와 모르는 주소는 홈이다", () => {
    for (const hash of ["", "#", "#/", "#/nope", "#/s/sess_1", "#/product_planning/question", "#/a/b/c/d/e", "#/s/sess_1/v/0", "#/s/sess_1/saved", "#/s/sess_1/saved/x", "#/s/sess_1/v/x", "#/s/sess_1/v/2/x"]) {
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
    expect(contextOf({ name: "failed", sessionId: "sess_1" })).toBe("session:sess_1");
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

describe("isListRoute", () => {
  it("홈·내 작업·결과물은 내 세션 목록을 쓰는 화면이다", () => {
    expect([HOME, { name: "work" }, { name: "documents" }].every((r) => isListRoute(r as Route))).toBe(true);
    expect(isListRoute({ name: "guide" })).toBe(false);
    expect(isListRoute({ name: "saved", sessionId: "s", version: 1 })).toBe(false);
  });

  it("목록 화면은 각자 다른 묶음이고, 저장 완료·버전 보기는 그 세션 묶음이다", () => {
    expect(contextOf({ name: "work" })).toBe("work");
    expect(contextOf({ name: "documents" })).toBe("documents");
    expect(contextOf({ name: "saved", sessionId: "s", version: 1 })).toBe(contextOf({ name: "version", sessionId: "s", version: 1 }));
  });
});

describe("문구 수정 주소", () => {
  it("edit 주소", () => {
    const route: Route = { name: "edit", sessionId: "sess_1", order: 2 };
    expect(toHash(route)).toBe("#/s/sess_1/edit/2");
    expect(parseRoute("#/s/sess_1/edit/2")).toEqual(route);
    expect(parseRoute("#/s/sess_1/edit/0")).toEqual({ name: "edit", sessionId: "sess_1", order: 0 });
    expect(parseRoute("#/s/sess_1/edit/x")).toEqual(HOME);
    expect(parseRoute("#/s/sess_1/edit/-1")).toEqual(HOME);
    expect(contextOf(route)).toBe("session:sess_1");
  });
});

describe("근거 검토 주소", () => {
  it("세션 묶음이다", () => {
    expect(contextOf({ name: "evidence", sessionId: "sess_1" })).toBe("session:sess_1");
    expect(sessionIdOf({ name: "evidence", sessionId: "sess_1" })).toBe("sess_1");
  });
});
