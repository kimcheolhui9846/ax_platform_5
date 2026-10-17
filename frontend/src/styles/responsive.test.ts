import { renderToString } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import { AppShell } from "../layout/AppShell";

const sheets = import.meta.glob("./*.css", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

const LAYOUT_MEDIA = /@media\s*\((?!\s*prefers-reduced-motion)/;

describe("반응형 배치", () => {
  it("배치용 @media는 거르고 움직임 줄이기 설정은 허용한다", () => {
    expect(LAYOUT_MEDIA.test("@media (max-width: 700px) { a { b: c } }")).toBe(true);
    expect(LAYOUT_MEDIA.test("@media (prefers-reduced-motion: reduce) { a { b: c } }")).toBe(false);
  });

  // 배치는 창 폭(@media)이 아니라 뼈대 폭(@container)으로 바뀌어야 미리보기의 390px 프레임이 스스로 모바일 배치가 된다.
  // 사용자 설정 질의(prefers-reduced-motion)는 배치 질의가 아니라서 허용한다.
  it("배치 규칙은 창 폭이 아니라 뼈대 폭을 기준으로 한다", () => {
    const offenders = Object.entries(sheets)
      .filter(([, css]) => LAYOUT_MEDIA.test(css))
      .map(([name]) => name);
    expect(offenders).toEqual([]);
    expect(sheets["./layout.css"]).toContain("@container app (max-width: 1099px)");
    expect(sheets["./layout.css"]).toContain("@container app (max-width: 719px)");
  });

  // 미리보기가 앱 배치를 고치는 곳은 프레임 안에서 창 높이(100vh)에 묶인 값을 푸는 두 규칙과 본문 바로가기 숨김뿐이다.
  it("미리보기는 앱 배치 규칙을 따로 베끼지 않는다", () => {
    const css = sheets["./preview.css"] ?? "";
    const selectors = [...css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{/g)].map((m) => m[1].trim());
    const touchingApp = selectors.filter((selector) => !/^\.gallery[\w-]*$/.test(selector));
    expect(touchingApp).toEqual([".gallery-frame .app-shell", ".gallery-frame .rail", ".gallery .skip"]);
    expect(css).not.toMatch(/@(media|container)\b/);
  });

  // html.to.design은 스크롤 상자 안에 숨은 부분을 잘린 채 가져온다. 프레임 바깥은 페이지 자체가 스크롤해야 한다.
  it("미리보기 프레임을 자르는 스크롤 상자가 없다", () => {
    const css = (sheets["./preview.css"] ?? "").replace(/\/\*[\s\S]*?\*\//g, "");
    const rules = [...css.matchAll(/([^{}]+)\{([^}]*)\}/g)].map((m) => ({ selector: m[1].trim(), body: m[2] }));
    // overflow·overflow-x·overflow-block 등 값이 하나라도 visible이 아니면 자른다
    const clips = (body: string) =>
      [...body.matchAll(/overflow(?:-[a-z]+)?\s*:\s*([^;]+)/g)].some((m) => m[1].trim().split(/\s+/).some((v) => v !== "visible"));
    const clipping = rules.filter((r) => r.selector !== ".gallery-frame" && clips(r.body)).map((r) => r.selector);
    expect(clipping).toEqual([]);
    expect(rules.find((r) => r.selector === ".gallery")?.body).toMatch(/width:\s*max-content/);
  });

  // 화면이 바뀔 때 앱이 본문(main)으로 초점을 옮긴다. 본문 전체에 초점 테두리가 그려지면 안 된다(버튼·입력창은 그대로).
  it("본문은 초점을 받아도 테두리를 그리지 않는다", () => {
    expect(sheets["./layout.css"]).toMatch(/\.app-main:focus\s*\{[^}]*outline:\s*none/);
  });

  // 입력창 자체는 테두리 없이 상자에 녹아 있으므로 초점은 상자(composer)가 보여 준다
  it("입력 상자는 안에 초점이 있으면 초점 테두리를 그린다", () => {
    expect(sheets["./screens.css"]).toMatch(/\.composer:focus-within\s*\{[^}]*outline:\s*var\(--focus-ring\)/);
  });

  it("안내 상자의 버튼은 글자 폭만큼, 좁은 화면의 모드 아래 줄은 접힌다", () => {
    const css = sheets["./screens.css"] ?? "";
    expect(css).toMatch(/\.notice\s*>\s*\.btn\s*\{[^}]*align-self:\s*flex-start/);
    const narrow = css.slice(css.indexOf("@container app (max-width: 719px)"));
    expect(narrow).toMatch(/\.mode-view\s*>\s*\.row\s*\{[^}]*flex-wrap:\s*wrap/);
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
