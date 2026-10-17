import { describe, expect, it } from "vitest";

import type { EvidenceItem, EvidenceRecord } from "../api/types";
import { appliedSourceIds, evidenceButton, proposalLabel, resultHeading, safeUrl, versionBeforeEvidence } from "./evidence";

const record = (source_id: string): EvidenceRecord => ({
  source_id,
  title: "제작 점검 항목",
  text: "점검 문구",
  note: "제품 시험 전",
  source_title: "제작 점검 · 지퍼 사용상 주의",
  publisher: "YKK KOREA",
  url: "https://example.com",
  section_kind: "suggestion",
  section_order: 2,
});

describe("근거 판단", () => {
  it("http(s) 주소만 링크로 쓴다", () => {
    expect(safeUrl("https://ykkkorea.com/a")).toBe("https://ykkkorea.com/a");
    expect(safeUrl("http://x.kr")).toBe("http://x.kr");
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("  ")).toBeNull();
  });

  it("반영한 자료 id를 결과의 기록에서 모은다", () => {
    expect([...appliedSourceIds([record("a"), record("b")])]).toEqual(["a", "b"]);
  });

  it("자료가 없는 과제는 검토 버튼이 없고, 반영 뒤에는 다시 보기다", () => {
    expect(evidenceButton(0, false)).toBeNull();
    expect(evidenceButton(2, false)).toEqual({ label: "근거 자료 검토 · 2건", primary: true });
    expect(evidenceButton(2, true)).toEqual({ label: "근거 자료 다시 보기", primary: false });
  });

  it("근거를 반영한 버전이면 반영 전 버전 번호를 준다", () => {
    expect(versionBeforeEvidence({ version: 3, reason: "evidence" })).toBe(2);
    expect(versionBeforeEvidence({ version: 3, reason: "edit" })).toBeNull();
    expect(versionBeforeEvidence({ version: 1, reason: "evidence" })).toBeNull();
  });

  it("결과 패널 제목은 근거를 반영한 버전에서 바뀐다", () => {
    expect(resultHeading("evidence")).toBe("검토 내용을 반영했어요");
    expect(resultHeading("first")).toBe("결과를 확인해 주세요");
  });

  it("반영할 내용 이름은 섹션 종류와 점검 항목이다", () => {
    const item = { applies_to: "suggestion", record: { title: "제작 점검 항목", text: "", note: "", caution: "" } } as EvidenceItem;
    expect(proposalLabel(item)).toBe("제안 · 제작 점검 항목");
  });
});
