import { describe, expect, it } from "vitest";

import { makeResult, makeTask } from "../testing/factories";
import { documentContent, documentSections, resultKicker, resultTitle } from "./document";

const v2 = { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate" as const, saved: false };

describe("결과 문서", () => {
  it("섹션을 순서대로 01, 02 …로, 본문은 글 블록을 잇는다", () => {
    const sections = documentSections([
      { order: 3, heading: "다음 실행", kind: "action", blocks: [{ type: "text", text: "다섯 명에게 묻기" }] },
      { order: 1, heading: "상품 콘셉트", kind: "diagnosis", blocks: [{ type: "text", text: "한글" }, { type: "text", text: "파우치" }] },
    ]);
    expect(sections).toEqual([
      { key: "diagnosis-1", number: "01", heading: "상품 콘셉트", tag: "진단", body: "한글\n\n파우치" },
      { key: "action-3", number: "02", heading: "다음 실행", tag: "실행 과제", body: "다섯 명에게 묻기" },
    ]);
  });

  it("결과에 반영한 보완 정보를 함께 싣는다", () => {
    const shown = makeResult({ supplements: [{ name: "material", label: "소재", example: "면 100%", value: "면" }] });
    expect(documentContent(makeTask(), shown, false).supplements).toEqual([{ label: "소재", value: "면" }]);
    expect(documentContent(makeTask(), makeResult(), false).supplements).toEqual([]);
  });

  it("제목과 위 작은 줄(버전 · 결과물 이름, 낡았으면 최신 아님)", () => {
    expect(resultTitle("상품기획")).toBe("상품기획 초안");
    expect(resultKicker("상품 콘셉트 · 첫 제작 기획서", v2, false)).toBe("V2 · 다시 만든 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(resultKicker("상품 콘셉트 · 첫 제작 기획서", v2, true)).toBe("V2 · 다시 만든 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
  });

  it("문서 내용은 그 결과(또는 버전)의 기준과 검토 항목으로 만든다", () => {
    const shown = makeResult({
      validation: { issues: [{ rule: "r", message: "확인해 주세요.", severity: "warning" }], passed: true },
      unknowns: [{ field: "mvp", label: "MVP 구성" }],
    });
    const content = documentContent(makeTask(), shown, false);
    expect(content.title).toBe("상품기획 초안");
    expect(content.kicker).toBe("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(content.rows.map((r) => r.value)).toEqual(["수제 향초", "아직 미정"]);
    expect(content.result).toBe(shown.result);
    expect(content.issues.map((i) => i.message)).toEqual(["확인해 주세요."]);
    expect(documentContent(makeTask(), { ...shown, validation: null }, false).issues).toEqual([]);
  });
});
