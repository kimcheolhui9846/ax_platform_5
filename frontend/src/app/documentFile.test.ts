import { describe, expect, it } from "vitest";

import { makeResult, makeSession, makeTask, makeVersionView } from "../testing/factories";
import { documentFileOf } from "./documentFile";

const task = makeTask();
const session = makeSession({ next_question: null, has_result: true, raw_input: "한글 파우치" });

describe("documentFileOf", () => {
  it("결과 화면은 지금 결과를, 저장 완료는 저장한 그 버전을 내려받는다", () => {
    const file = documentFileOf({ kind: "result", task, session, result: makeResult() });
    expect(file?.filename).toBe("AX_product_planning_V1.html");
    expect(file?.html).toContain("한글 파우치");

    const saved = makeVersionView({ version: { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: true } });
    expect(documentFileOf({ kind: "saved", task, session, version: saved })?.filename).toBe("AX_product_planning_V2.html");
  });

  it("지금 버전이라도 답이 바뀌어 결과가 낡았으면 최신 아님을 붙인다", () => {
    const stale = makeSession({ next_question: null, has_result: true, result_stale: true });
    const file = documentFileOf({ kind: "version", task, session: stale, version: makeVersionView() });
    expect(file?.html).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });

  it("버전 보기는 그 버전을 내려받고, 지난 버전이면 최신 아님을 붙인다", () => {
    const old = makeVersionView({
      latest: false,
      version: { version: 3, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: true },
    });
    const file = documentFileOf({ kind: "version", task, session, version: old });
    expect(file?.filename).toBe("AX_product_planning_V3.html");
    expect(file?.html).toContain("V3 · 다시 만든 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });

  it("결과가 없는 화면은 내려받을 문서가 없다", () => {
    expect(documentFileOf({ kind: "result", task, session, result: null })).toBeNull();
    expect(documentFileOf({ kind: "guide" })).toBeNull();
  });
});
