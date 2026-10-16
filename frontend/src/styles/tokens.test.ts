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

  // vitest가 CSS를 빈 문자열로 바꾸면(test.css 꺼짐) 아래 검사가 모두 헛돌므로 먼저 막는다.
  it("CSS 원문을 읽는다", () => {
    const empty = Object.entries(sheets)
      .filter(([, css]) => css.trim() === "")
      .map(([name]) => name);
    expect(empty).toEqual([]);
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

  // 피그마에서 고치는 값(글자 크기·폭·선 두께·모서리)은 tokens.css 한 곳에서 바꿀 수 있어야 한다. 안쪽 여백의 잔값과 위치 값은 예외다.
  it("글자 크기·폭·선·모서리 값은 tokens.css 변수로만 쓴다", () => {
    const DESIGN_PROPS = /(?:^|[;{\s])(font-size|(?:min-|max-)?width|border(?:-[a-z]+)*)\s*:\s*([^;}]*)/g;
    const offenders = Object.entries(sheets)
      .filter(([name]) => name !== "./tokens.css")
      .flatMap(([name, css]) =>
        [...css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(DESIGN_PROPS)]
          .filter((m) => /\d+(\.\d+)?px/.test(m[2]))
          .map((m) => `${name} ${m[1]}: ${m[2].trim()}`),
      );
    expect(offenders).toEqual([]);
  });
});
