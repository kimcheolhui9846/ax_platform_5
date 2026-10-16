import type { Question, ResultView, SessionView, TaskSummary } from "../api/types";

/**
 * 지금 보여 줄 화면. 설계서 9.3의 여섯 상태와 맞춘다.
 * 초기 = pick_task·idea, 정보 부족 = clarifying, 생성 중 = generating, 완료 = result, 실패 = failed, 수정 = revising.
 * ready는 정보가 모여 결과를 만들기만 하면 되는 상태(초기와 생성 중 사이)다.
 */
export type Screen =
  | { kind: "pick_task" }
  | { kind: "idea"; task: TaskSummary }
  | { kind: "clarifying"; session: SessionView; question: Question }
  | { kind: "ready"; session: SessionView }
  | { kind: "revising"; session: SessionView }
  | { kind: "generating"; session: SessionView }
  | { kind: "failed"; session: SessionView; question: Question | null }
  | { kind: "result"; result: ResultView };

export function screenOf(
  task: TaskSummary | null,
  session: SessionView | null,
  result: ResultView | null,
): Screen {
  if (!task) return { kind: "pick_task" };
  if (!session) return { kind: "idea", task };
  if (result) return { kind: "result", result };
  if (session.status === "generating") return { kind: "generating", session };
  if (session.status === "failed") return { kind: "failed", session, question: session.next_question };
  if (session.next_question) return { kind: "clarifying", session, question: session.next_question };
  if (session.result_stale) return { kind: "revising", session };
  return { kind: "ready", session };
}

/** 결과가 지금 답과 맞지 않을 때(답을 고쳤거나 재생성이 실패했을 때) 보여 줄 안내. */
export const STALE_HINT = "결과가 최신이 아님 — 바뀐 답을 반영하려면 결과를 다시 만들어 주세요.";
