import { describe, expect, it } from "vitest";

import type { EvidenceRecord, ResultSection } from "../api/types";
import { makeResult, makeTask } from "../testing/factories";
import { documentContent, documentSections, firstSectionOrder, resultKicker, resultTitle, trailingRecords } from "./document";

const v2 = { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate" as const, saved: false };

describe("결과 문서", () => {
  it("섹션을 순서대로 01, 02 …로, 글 블록은 순서대로 담는다", () => {
    const sections = documentSections([
      { order: 3, heading: "다음 실행", kind: "action", blocks: [{ type: "text", text: "다섯 명에게 묻기" }] },
      { order: 1, heading: "상품 콘셉트", kind: "diagnosis", blocks: [{ type: "text", text: "한글" }, { type: "text", text: "파우치" }] },
    ], [], {});
    expect(sections).toEqual([
      { key: "diagnosis-1", number: "01", heading: "상품 콘셉트", tag: "진단", blocks: [{ kind: "text", key: "0", text: "한글" }, { kind: "text", key: "1", text: "파우치" }], records: [] },
      { key: "action-3", number: "02", heading: "다음 실행", tag: "실행 과제", blocks: [{ kind: "text", key: "0", text: "다섯 명에게 묻기" }], records: [] },
    ]);
  });

  it("결과에 반영한 보완 정보를 함께 싣는다", () => {
    const shown = makeResult({ supplements: [{ name: "material", label: "소재", example: "면 100%", value: "면", private: false }] });
    expect(documentContent(makeTask(), shown, false, {}).supplements).toEqual([{ label: "소재", value: "면" }]);
    expect(documentContent(makeTask(), makeResult(), false, {}).supplements).toEqual([]);
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
    const content = documentContent(makeTask(), shown, false, {});
    expect(content.title).toBe("상품기획 초안");
    expect(content.kicker).toBe("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(content.rows.map((r) => r.value)).toEqual(["수제 향초", "아직 미정"]);
    expect(content.result).toBe(shown.result);
    expect(content.issues.map((i) => i.message)).toEqual(["확인해 주세요."]);
    expect(documentContent(makeTask(), { ...shown, validation: null }, false, {}).issues).toEqual([]);
  });

  it("첫 섹션 번호(순서가 가장 앞선 섹션). 섹션이 없으면 null", () => {
    const section = (order: number) => ({ order, heading: "h", kind: "diagnosis" as const, blocks: [] });
    expect(firstSectionOrder([section(3), section(2)])).toBe(2);
    expect(firstSectionOrder([])).toBeNull();
  });
});

const sections: ResultSection[] = [
  { order: 1, heading: "콘셉트", kind: "diagnosis", blocks: [{ type: "text", text: "글" }] },
  {
    order: 2,
    heading: "제작 방향",
    kind: "suggestion",
    blocks: [
      { type: "text", text: "방향" },
      { type: "image", asset_id: "asset_a", alt: "제작 방향 참고 이미지", caption: "AI 참고 이미지", origin: "ai_generated" },
    ],
  },
];
const zipper: EvidenceRecord = {
  source_id: "zip",
  title: "제작 점검 항목",
  text: "여닫기를 점검합니다.",
  note: "제품 시험 전",
  source_title: "지퍼 사용상 주의",
  publisher: "YKK KOREA",
  url: "https://ykkkorea.com/a",
  section_kind: "suggestion",
  section_order: 2,
};

describe("문서 블록과 근거 기록", () => {
  it("글과 이미지 블록을 순서대로, 이미지는 불러온 주소와 함께 낸다", () => {
    const [, second] = documentSections(sections, [], { asset_a: "data:image/svg+xml;base64,AA" });
    expect(second.blocks).toEqual([
      { kind: "text", key: "0", text: "방향" },
      { kind: "image", key: "1", src: "data:image/svg+xml;base64,AA", alt: "제작 방향 참고 이미지", caption: "AI 참고 이미지" },
    ]);
    expect(documentSections(sections, [], {})[1].blocks[1]).toMatchObject({ kind: "image", src: null });
  });

  it("근거 기록은 자리 잡은 섹션 뒤에, 자리가 없으면 문서 끝에 둔다", () => {
    const placed = documentSections(sections, [zipper], {});
    expect(placed[0].records).toEqual([]);
    expect(placed[1].records).toEqual([
      {
        key: "zip",
        label: "근거 검토 반영 · 제작 점검 항목",
        text: "여닫기를 점검합니다.",
        source: "출처: YKK KOREA · 지퍼 사용상 주의",
        note: "제품 시험 전",
        url: "https://ykkkorea.com/a",
      },
    ]);
    expect(trailingRecords(sections, [zipper])).toEqual([]);
    const loose = { ...zipper, section_order: null, url: "javascript:x" };
    expect(trailingRecords(sections, [loose])).toMatchObject([{ key: "zip", url: null }]);
  });
});
