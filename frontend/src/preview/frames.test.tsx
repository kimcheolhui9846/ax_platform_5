import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import previewCss from "../styles/preview.css?raw";
import { FRAMES, FRAME_SIZES } from "./frames";
import { Gallery } from "./Gallery";

describe("미리보기 프레임", () => {
  it("이름이 겹치지 않고 비어 있지 않다", () => {
    const ids = FRAMES.map((f) => f.id);
    expect(ids.length).toBeGreaterThan(0);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("묶음 0 화면 상태를 모두 담는다", () => {
    expect(FRAMES.map((f) => f.id)).toEqual(["home", "idea", "question", "question-ladder", "ready", "result"]);
  });

  it.each(FRAMES)("$id 프레임이 깨지지 않고 그려진다", (frame) => {
    const html = renderToString(frame.render(`${frame.id}-main`));
    expect(html.length).toBeGreaterThan(0);
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
    expect(ids.length).toBe(FRAMES.length * 2);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) expect(html).toContain(`href="#${id}"`);
  });
});
