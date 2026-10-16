import { describe, expect, it } from "vitest";

import { questionHint } from "./questionHint";

describe("questionHint", () => {
  it("기본 질문(level 0)에는 안내가 없다", () => {
    expect(questionHint({ level: 0, is_ai_proposal: false })).toBeNull();
  });

  it("사다리 단계의 쉬운 질문에는 쉬운 질문 안내를 쓴다", () => {
    expect(questionHint({ level: 1, is_ai_proposal: false })).toBe("조금 더 쉽게 물어볼게요.");
  });

  it("AI 제안 단계에는 후보 안내를 쓴다", () => {
    expect(questionHint({ level: 2, is_ai_proposal: true })).toBe(
      "AI가 추정한 후보예요. 가장 가까운 걸 고르거나 직접 고쳐 주세요.",
    );
  });
});
