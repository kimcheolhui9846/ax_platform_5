import { describe, expect, it } from "vitest";

import type { SupplementItem } from "../api/types";
import { ALL_FILLED_NOTE, appliedRows, panelAfter, supplementDraft, supplementStatus, supplementValues } from "./supplements";

const item = (name: string, label: string, value: string | null): SupplementItem => ({ name, label, example: "", value, private: false });

describe("supplementStatus", () => {
  const empty = [item("material", "소재", null), item("size", "크기", null)];

  it("아무것도 입력하지 않았으면 입력을 안내하고, 반영할 것이 없다", () => {
    expect(supplementStatus(empty, empty, false, true)).toEqual({
      line: "입력 0/2 · 보완할 정보를 입력해 주세요",
      missing: "미확인: 소재 · 크기",
      canApply: false,
    });
  });

  it("입력이 초안에 반영되지 않았으면 반영할 수 있다", () => {
    const current = [item("material", "소재", "면"), item("size", "크기", null)];
    expect(supplementStatus(current, empty, true, true)).toEqual({ line: "입력 1/2 · 아직 초안에 미반영", missing: "미확인: 크기", canApply: true });
  });

  it("반영한 뒤에는 반영됨이고, 모두 채웠으면 검증 전임을 알린다", () => {
    const filled = [item("material", "소재", "면"), item("size", "크기", "20cm")];
    expect(supplementStatus(filled, filled, false, true)).toEqual({ line: "입력 2/2 · 초안에 반영됨", missing: ALL_FILLED_NOTE, canApply: false });
  });
});

describe("대화상자 값", () => {
  it("처음 값은 지금 입력(미확인은 빈 글), 저장할 값은 빈 글이 미확인(null)이다", () => {
    expect(supplementDraft([item("material", "소재", "면"), item("size", "크기", null)])).toEqual({ material: "면", size: "" });
    expect(supplementValues({ material: "  리넨 ", size: "  " })).toEqual({ material: "리넨", size: null });
  });
});

describe("appliedRows", () => {
  it("결과에 반영한 보완 정보. 하나도 없으면 칸을 두지 않는다", () => {
    expect(appliedRows([item("material", "소재", null)])).toEqual([]);
    expect(appliedRows([item("material", "소재", "면"), item("size", "크기", null)])).toEqual([
      { label: "소재", value: "면", private: false },
      { label: "크기", value: "미확인", private: false },
    ]);
  });

  it("비공개였던 보완 정보는 표시를 싣는다", () => {
    expect(appliedRows([{ ...item("price", "판매 가격", "18,000원"), private: true }])).toEqual([
      { label: "판매 가격", value: "18,000원", private: true },
    ]);
  });
});

describe("supplementStatus 생성 가능 여부", () => {
  it("바뀌었어도 지금 생성할 수 없으면 초안에 반영을 누를 수 없다", () => {
    const current = [item("material", "소재", "면")];
    expect(supplementStatus(current, [], true, false).canApply).toBe(false);
    expect(supplementStatus(current, [], true, true).canApply).toBe(true);
  });
});

describe("panelAfter(보완 대화상자 단계)", () => {
  it("닫힘에서 열기만 열린다", () => {
    expect(panelAfter("closed", { type: "open" })).toBe("open");
    expect(panelAfter("closed", { type: "cancel" })).toBe("closed");
  });

  it("열린 채 취소하면 닫히고, 저장하면 연 채 저장 중이다", () => {
    expect(panelAfter("open", { type: "cancel" })).toBe("closed");
    expect(panelAfter("open", { type: "save" })).toBe("saving");
  });

  it("저장 중에는 취소·다시 저장을 받지 않는다", () => {
    expect(panelAfter("saving", { type: "cancel" })).toBe("saving");
    expect(panelAfter("saving", { type: "save" })).toBe("saving");
  });

  it("저장이 끝나면 성공은 닫고 실패는 연 채 입력을 살린다", () => {
    expect(panelAfter("saving", { type: "settled", saved: true })).toBe("closed");
    expect(panelAfter("saving", { type: "settled", saved: false })).toBe("open");
  });

  it("저장 중이 아닐 때 온 끝남 신호는 무시한다", () => {
    expect(panelAfter("open", { type: "settled", saved: true })).toBe("open");
    expect(panelAfter("closed", { type: "settled", saved: false })).toBe("closed");
  });
});
