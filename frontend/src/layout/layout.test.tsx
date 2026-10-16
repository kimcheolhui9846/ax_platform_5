import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { railItems } from "../lib/shell";
import { AppShell } from "./AppShell";

const noop = () => {};

function shell(side: ReactNode | null = null) {
  return renderToString(
    <AppShell
      rail={{ items: railItems("home", new Set(["home"])), onNavigate: noop }}
      header={{ project: "상품기획", phase: 1, onPickTask: noop }}
      side={side}
    >
      <p>본문</p>
    </AppShell>,
  );
}

describe("AppShell", () => {
  it("본문 바로가기, 주 메뉴, 활성 항목, 본문을 그린다", () => {
    const html = shell();
    expect(html).toContain('href="#main"');
    expect(html).toContain('aria-label="주 메뉴"');
    expect(html).toContain('aria-current="page"');
    expect(html).toContain('id="main"');
    expect(html).toContain("본문");
  });

  it("헤더에 과제 이름과 현재 단계를 그린다", () => {
    const html = shell();
    expect(html).toContain("상품기획");
    expect(html).toContain('<span class="header-step is-current">2 함께 구체화</span>');
  });

  it("오른쪽 패널은 있을 때만 그린다", () => {
    expect(shell()).not.toContain("app-side");
    expect(shell(<p>흐름</p>)).toContain("app-side");
  });

  it("과제 밖이면 작업 공간 문구를 보여 주고 단계는 없다", () => {
    const html = renderToString(
      <AppShell
        rail={{ items: railItems("home", new Set(["home"])), onNavigate: noop }}
        header={{ project: null, phase: null, onPickTask: noop }}
      >
        <p>홈</p>
      </AppShell>,
    );
    expect(html).toContain("내 창작 작업 공간");
    expect(html).not.toContain('<span class="header-step');
  });
});
