import type { Question } from "../api/types";

type Level = Pick<Question, "level" | "is_ai_proposal">;

/** 질문 카드 위 작은 제목. 첫 기본 질문은 핵심 질문, 사다리 질문은 다른 예시·AI 후보로 구분한다.
 * answeredBefore는 지금 질문 앞에 이미 물어본 필드 수다(flowView의 answeredBefore). */
export function questionKicker(question: Level, answeredBefore: number): string {
  if (question.is_ai_proposal) return "AI 후보 제안";
  if (question.level > 0) return "다른 예시";
  return answeredBefore === 0 ? "핵심 질문" : "추가 질문";
}

/** 질문 아래 안내. */
export function questionHint(question: Level): string {
  if (question.is_ai_proposal) return "AI가 추정한 후보예요. 가장 가까운 걸 고르거나 직접 고쳐 주세요.";
  if (question.level > 0) return "조금 더 쉽게 물어볼게요. 가까운 답을 골라 주세요.";
  return "정답은 없어요. 지금 생각과 가장 가까운 답을 골라 주세요.";
}

export type ExampleAction = { action: "easier" | "original"; label: string };

/** '다른 예시 보기'는 모든 질문에 있다. 사다리에 들어가 있으면 기본 질문으로 돌아가는 '원래 예시 보기'도 보인다. */
export function exampleActions(question: Pick<Question, "level">): ExampleAction[] {
  const easier: ExampleAction = { action: "easier", label: "다른 예시 보기" };
  return question.level > 0 ? [easier, { action: "original", label: "원래 예시 보기" }] : [easier];
}
