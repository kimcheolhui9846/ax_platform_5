import { describe, expect, it } from "vitest";

import { makeResult, makeSession, makeTask, makeVersionView } from "../testing/factories";
import { documentHtml } from "../lib/documentHtml";
import { documentFileOf } from "./documentFile";

const html = (file: ReturnType<typeof documentFileOf>) => (file === null ? "" : documentHtml(file.content));
const task = makeTask();
const session = makeSession({ next_question: null, has_result: true, raw_input: "한글 파우치", name: "" });

describe("documentFileOf", () => {
  it("결과 화면은 지금 결과를, 저장 완료는 저장한 그 버전을 내려받는다", () => {
    const file = documentFileOf({ kind: "result", task, session, result: makeResult(), images: {} });
    expect(file?.basename).toBe("AX_product_planning_V1");
    expect(file?.content.request).toBe("한글 파우치");
    expect(html(file)).toContain("한글 파우치");

    const saved = makeVersionView({ version: { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: true } });
    expect(documentFileOf({ kind: "saved", task, session, version: saved, images: {}, next: null })?.basename).toBe("AX_product_planning_V2");
  });

  it("파일 이름은 작업 이름으로 만들고, 쓸 수 없는 문자는 뺀다", () => {
    const named = makeSession({ next_question: null, has_result: true, name: "수제 향초: 기획/안" });
    expect(documentFileOf({ kind: "result", task, session: named, result: makeResult(), images: {} })?.basename).toBe("수제 향초 기획안_V1");
  });

  it("지금 버전이라도 답이 바뀌어 결과가 낡았으면 최신 아님을 붙인다", () => {
    const stale = makeSession({ next_question: null, has_result: true, result_stale: true });
    const file = documentFileOf({ kind: "version", task, session: stale, version: makeVersionView(), images: {} });
    expect(html(file)).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });

  it("버전 보기는 그 버전을 내려받고, 지난 버전이면 최신 아님을 붙인다", () => {
    const old = makeVersionView({
      latest: false,
      version: { version: 3, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: true },
    });
    const file = documentFileOf({ kind: "version", task, session, version: old, images: {} });
    expect(file?.basename).toBe("AX_product_planning_V3");
    expect(html(file)).toContain("V3 · 다시 만든 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });

  it("결과가 없는 화면은 내려받을 문서가 없다", () => {
    expect(documentFileOf({ kind: "result", task, session, result: null, images: {} })).toBeNull();
    expect(documentFileOf({ kind: "guide" })).toBeNull();
  });

  it("받아 둔 이미지는 파일 안에 data URL로 들어간다", () => {
    const base = makeResult();
    const result = {
      ...base,
      result: {
        ...base.result,
        sections: [
          {
            order: 1,
            heading: "h",
            kind: "suggestion" as const,
            blocks: [{ type: "image" as const, asset_id: "a", alt: "참고", caption: "", origin: "ai_generated" as const }],
          },
        ],
      },
    };
    const file = documentFileOf({ kind: "result", task, session, result, images: { a: "data:image/svg+xml;base64,AA" } });
    expect(html(file)).toContain("data:image/svg+xml;base64,AA");
  });
});
