import { describe, expect, it } from "vitest";

import { HEADER_STEPS, enabledNav, headerSteps, railActive, railItems, routePhase } from "./shell";

describe("headerSteps", () => {
  it("과제 밖(null)이면 단계가 없다", () => {
    expect(headerSteps(null)).toEqual([]);
  });

  it("현재 단계만 current다", () => {
    expect(headerSteps(1)).toEqual([
      { label: HEADER_STEPS[0], current: false },
      { label: HEADER_STEPS[1], current: true },
      { label: HEADER_STEPS[2], current: false },
    ]);
  });
});

describe("railItems", () => {
  it("홈·내 작업·결과물 순서이고, 활성과 사용 가능 여부를 표시한다", () => {
    expect(railItems("home", new Set(["home"]))).toEqual([
      { key: "home", label: "홈", active: true, disabled: false },
      { key: "work", label: "내 작업", active: false, disabled: true },
      { key: "documents", label: "결과물", active: false, disabled: true },
    ]);
  });

  it("아무 것도 활성이 아닐 수 있다", () => {
    expect(railItems(null, new Set(["home", "work", "documents"])).every((i) => !i.active && !i.disabled)).toBe(true);
  });
});

describe("enabledNav", () => {
  it("메뉴 세 개를 모두 연다", () => {
    expect([...enabledNav(false)]).toEqual(["home", "work", "documents"]);
  });

  // 요청 중에 다른 화면으로 떠나면 늦게 온 응답이 버려진다(헤더 '과제 선택'과 같은 규칙).
  it("요청 중에는 모든 메뉴를 막는다", () => {
    expect(enabledNav(true).size).toBe(0);
    expect(railItems("home", enabledNav(true)).every((item) => item.disabled)).toBe(true);
  });
});

describe("묶음 2 주소의 단계와 메뉴", () => {
  it("저장 완료·버전 보기는 3단계, 목록 화면은 과제 밖이다", () => {
    expect(routePhase({ name: "saved", sessionId: "s" })).toBe(2);
    expect(routePhase({ name: "version", sessionId: "s", version: 1 })).toBe(2);
    expect(routePhase({ name: "work" })).toBeNull();
    expect(routePhase({ name: "documents" })).toBeNull();
  });

  it("내 작업은 내 작업, 결과·저장 완료·버전·결과물은 결과물 메뉴다", () => {
    expect(railActive({ name: "work" })).toBe("work");
    for (const route of [
      { name: "documents" },
      { name: "result", sessionId: "s" },
      { name: "saved", sessionId: "s" },
      { name: "version", sessionId: "s", version: 1 },
    ] as const) {
      expect(railActive(route)).toBe("documents");
    }
  });
});

describe("routePhase", () => {
  it("요청은 1단계, 모드·질문·고치기·확인은 2단계, 결과는 3단계, 홈·안내는 과제 밖이다", () => {
    expect(routePhase({ name: "home" })).toBeNull();
    expect(routePhase({ name: "guide" })).toBeNull();
    expect(routePhase({ name: "request", task: "t" })).toBe(0);
    expect(routePhase({ name: "mode", task: "t" })).toBe(1);
    expect(routePhase({ name: "question", sessionId: "s" })).toBe(1);
    expect(routePhase({ name: "revise", sessionId: "s", questionId: "q" })).toBe(1);
    expect(routePhase({ name: "confirm", sessionId: "s" })).toBe(1);
    expect(routePhase({ name: "result", sessionId: "s" })).toBe(2);
  });
});

describe("railActive", () => {
  it("홈·안내는 홈, 진행 중인 과제는 내 작업, 결과는 결과물이다", () => {
    expect(railActive({ name: "home" })).toBe("home");
    expect(railActive({ name: "guide" })).toBe("home");
    expect(railActive({ name: "request", task: "t" })).toBe("work");
    expect(railActive({ name: "confirm", sessionId: "s" })).toBe("work");
    expect(railActive({ name: "result", sessionId: "s" })).toBe("documents");
  });
});
