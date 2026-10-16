import { renderToString } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import { AppShell } from "../layout/AppShell";

const sheets = import.meta.glob("./*.css", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

describe("반응형 배치", () => {
  // 창 폭(@media)이 아니라 뼈대 폭(@container)으로 바뀌어야 미리보기의 390px 프레임이 스스로 모바일 배치가 된다.
  it("배치 규칙은 창 폭이 아니라 뼈대 폭을 기준으로 한다", () => {
    const offenders = Object.entries(sheets)
      .filter(([, css]) => /@media\s*\(/.test(css))
      .map(([name]) => name);
    expect(offenders).toEqual([]);
    expect(sheets["./layout.css"]).toContain("@container app (max-width: 1099px)");
    expect(sheets["./layout.css"]).toContain("@container app (max-width: 719px)");
  });

  it("미리보기는 모바일 배치를 따로 베끼지 않는다", () => {
    expect(sheets["./preview.css"]).not.toContain("-mobile");
  });

  it("뼈대가 스스로 폭 기준 컨테이너를 만든다", () => {
    const html = renderToString(
      createElement(AppShell, {
        rail: { items: [], onNavigate: () => {} },
        header: { project: null, phase: null, onPickTask: () => {} },
        children: createElement("p", null, "본문"),
      }),
    );
    expect(html.startsWith('<div class="app-viewport"><div class="app-shell">')).toBe(true);
    expect(sheets["./layout.css"]).toMatch(/\.app-viewport\s*\{[^}]*container:\s*app\s*\/\s*inline-size/);
  });
});
