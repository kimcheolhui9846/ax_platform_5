import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import previewCss from "../styles/preview.css?raw";
import { CONTEXT } from "./fixtures";
import { FRAMES, FRAME_SIZES } from "./frames";
import { Gallery } from "./Gallery";

// 디자인 V2(design/2026-10-16-ux-v2)의 화면 가운데 지금까지 만든 것. 묶음마다 늘린다.
const DESIGN_SCREENS = ["home", "request", "mode", "question", "confirm", "generating", "failed", "result", "guide", "work", "documents", "saved", "version", "edit", "evidence"];

describe("미리보기 프레임", () => {
  it("이름이 겹치지 않는다", () => {
    const ids = FRAMES.map((f) => f.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("묶음 3b까지의 화면 상태를 모두 담는다", () => {
    expect(FRAMES.map((f) => f.id)).toEqual([
      "home",
      "home-new",
      "request",
      "request-context",
      "request-notice",
      "mode",
      "question",
      "question-ladder",
      "question-proposal",
      "question-private",
      "revise",
      "confirm",
      "confirm-context",
      "confirm-private",
      "generating",
      "failed",
      "failed-with-result",
      "result",
      "result-stale",
      "result-supplement",
      "result-supplemented",
      "result-evidence",
      "result-image",
      "supplement-form",
      "edit",
      "evidence",
      "evidence-applied",
      "saved",
      "version",
      "work",
      "work-empty",
      "documents",
      "documents-empty",
      "guide",
      "unavailable",
    ]);
  });

  it("디자인 V2 화면이 갤러리에 빠짐없이 있다", () => {
    for (const screen of DESIGN_SCREENS) {
      expect(FRAMES.some((f) => f.id === screen || f.id.startsWith(`${screen}-`)), screen).toBe(true);
    }
  });

  it.each(FRAMES)("$id 프레임이 깨지지 않고 그려진다", (frame) => {
    expect(renderToString(frame.render(`${frame.id}-main`)).length).toBeGreaterThan(0);
  });

  it("갤러리는 프레임마다 PC·모바일 폭 두 개를 이름표와 함께 그린다", () => {
    const html = renderToString(<Gallery />);
    for (const frame of FRAMES) {
      expect(html).toContain(`data-screen="${frame.id}-desktop"`);
      expect(html).toContain(`data-screen="${frame.id}-mobile"`);
      expect(html).toContain(frame.title);
    }
    for (const size of FRAME_SIZES) {
      expect(html).toContain(`class="gallery-frame gallery-frame-${size}"`);
      // 프레임 폭은 tokens.css(--preview-desktop·--preview-mobile) 한 곳에서 정한다.
      expect(previewCss).toMatch(new RegExp(String.raw`\.gallery-frame-${size}\s*\{\s*width:\s*var\(--preview-${size}\)`));
    }
  });

  it("한 페이지에 여러 프레임을 그려도 id가 겹치지 않고 각 본문 바로가기는 자기 본문을 가리킨다", () => {
    const html = renderToString(<Gallery />);
    const ids = [...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
    expect(new Set(ids).size).toBe(ids.length);
    const mains = [...html.matchAll(/<main id="([^"]+)"/g)].map((m) => m[1]);
    expect(mains).toHaveLength(FRAMES.length * FRAME_SIZES.length);
    for (const id of mains) expect(html).toContain(`href="#${id}"`);
  });
});

describe("이어가기 샘플", () => {
  it("백엔드가 만들 수 있는 모양이다: 사업계획 V2에서 상품기획 필드로", () => {
    expect(CONTEXT.task_type).toBe("business_plan");
    expect(CONTEXT.title).toBe(`사업계획 초안 V${CONTEXT.version}`);
    expect(CONTEXT.items.map((i) => [i.field, i.label])).toEqual([
      ["product_idea", "상품 아이디어"],
      ["user", "사용자"],
    ]);
  });
});
