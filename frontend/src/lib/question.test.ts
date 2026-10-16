import { describe, expect, it } from "vitest";

import { exampleActions, questionHint, questionKicker } from "./question";

const base = { level: 0, is_ai_proposal: false };
const ladder = { level: 2, is_ai_proposal: false };
const proposal = { level: 4, is_ai_proposal: true };

describe("질문 카드 문구", () => {
  it("첫 기본 질문은 핵심 질문, 다음은 추가 질문, 사다리는 다른 예시·AI 후보", () => {
    expect(questionKicker(base, 0)).toBe("핵심 질문");
    expect(questionKicker(base, 2)).toBe("추가 질문");
    expect(questionKicker(ladder, 2)).toBe("다른 예시");
    expect(questionKicker(proposal, 2)).toBe("AI 후보 제안");
  });

  it("단계마다 다른 안내", () => {
    expect(questionHint(base)).toContain("정답은 없어요");
    expect(questionHint(ladder)).toContain("조금 더 쉽게");
    expect(questionHint(proposal)).toContain("AI가 추정한 후보");
  });

  it("'다른 예시 보기'는 늘 있고, 사다리에서는 '원래 예시 보기'도 있다", () => {
    expect(exampleActions(base).map((a) => a.action)).toEqual(["easier"]);
    expect(exampleActions(ladder)).toEqual([
      { action: "easier", label: "다른 예시 보기" },
      { action: "original", label: "원래 예시 보기" },
    ]);
  });
});
