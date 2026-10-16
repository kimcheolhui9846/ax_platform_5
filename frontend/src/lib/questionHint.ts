import type { Question } from "../api/types";

/** '모르겠어요' 사다리 단계에서만 질문 위에 안내를 보여 준다. */
export function questionHint(question: Pick<Question, "level" | "is_ai_proposal">): string | null {
  if (question.level <= 0) return null;
  return question.is_ai_proposal
    ? "AI가 추정한 후보예요. 가장 가까운 걸 고르거나 직접 고쳐 주세요."
    : "조금 더 쉽게 물어볼게요.";
}
