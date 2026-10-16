import type { Question, ResultView, SessionView, TaskSummary } from "../api/types";

/**
 * 지금 보여 줄 화면. 설계서 9.3의 여섯 상태와 맞춘다.
 * 초기 = pick_task·idea, 정보 부족 = clarifying, 생성 중 = generating, 완료 = result·completed, 실패 = failed, 수정 = revising.
 * ready는 정보가 모여 결과를 만들기만 하면 되는 상태(초기와 생성 중 사이)다.
 * completed는 결과가 지금 답과 맞고 더 물을 것도 없는 세션 화면이다(결과 보기로 돌아갈 수 있다).
 */
export type Screen =
  | { kind: "pick_task" }
  | { kind: "idea"; task: TaskSummary }
  | { kind: "clarifying"; session: SessionView; question: Question }
  | { kind: "ready"; session: SessionView }
  | { kind: "revising"; session: SessionView }
  | { kind: "completed"; session: SessionView }
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
  if (session.status === "completed") return { kind: "completed", session };
  return { kind: "ready", session };
}

/** 결과가 지금 답과 맞지 않을 때(결과를 만든 뒤 답을 고치거나 더 답했을 때) 보여 줄 안내. */
export const STALE_HINT = "결과가 최신이 아님 — 바뀐 답을 반영하려면 결과를 다시 만들어 주세요.";

export type SessionAction = {
  action: "show_result" | "generate" | "regenerate";
  label: string;
};

/**
 * 세션 화면 아래쪽 버튼. 결과가 최신이면 이미 있는 결과를 보는 것이 먼저다(다시 만들면 LLM 호출이 든다).
 * 결과가 최신이 아니면 다시 만드는 것이 먼저이고, 이전 결과도 볼 수 있다.
 */
export function sessionActions(
  session: Pick<SessionView, "has_result" | "result_stale">,
): { primary: SessionAction; secondary: SessionAction | null } {
  if (!session.has_result) {
    return { primary: { action: "generate", label: "이대로 결과 만들기" }, secondary: null };
  }
  if (session.result_stale) {
    return {
      primary: { action: "regenerate", label: "결과 다시 만들기" },
      secondary: { action: "show_result", label: "이전 결과 보기" },
    };
  }
  return {
    primary: { action: "show_result", label: "결과 보기" },
    secondary: { action: "regenerate", label: "다시 만들기" },
  };
}

/** 세션 화면 버튼 하나의 이름과 막힘. 결과 보기는 LLM을 부르지 않으므로 생성 가능 여부와 상관없다. */
export function actionButton(
  action: SessionAction,
  { busy, canGenerate }: { busy: boolean; canGenerate: boolean },
): { label: string; disabled: boolean } {
  const calls = action.action !== "show_result";
  return {
    label: busy && calls ? "처리 중…" : action.label,
    disabled: busy || (calls && !canGenerate),
  };
}
