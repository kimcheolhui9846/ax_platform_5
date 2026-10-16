import { describe, expect, it } from "vitest";

// Vite가 빌드 시점에 CSS 원문을 문자열로 넣어 준다(node 타입 없이 동작).
const sheets = import.meta.glob("./*.css", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

const RAW_COLOR = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/;

function definedVars(css: string): Set<string> {
  return new Set([...css.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));
}

function usedVars(css: string): string[] {
  return [...css.matchAll(/var\((--[a-z0-9-]+)/g)].map((m) => m[1]);
}

describe("디자인 토큰", () => {
  it("tokens.css가 있다", () => {
    expect(Object.keys(sheets)).toContain("./tokens.css");
  });

  it("원시 색상은 tokens.css에만 있다", () => {
    const offenders = Object.entries(sheets)
      .filter(([name]) => name !== "./tokens.css")
      .filter(([, css]) => RAW_COLOR.test(css))
      .map(([name]) => name);
    expect(offenders).toEqual([]);
  });

  it("쓰는 변수는 모두 tokens.css에 정의돼 있다", () => {
    const defined = definedVars(sheets["./tokens.css"] ?? "");
    const missing = Object.values(sheets)
      .flatMap(usedVars)
      .filter((name) => !defined.has(name));
    expect([...new Set(missing)]).toEqual([]);
  });
});
