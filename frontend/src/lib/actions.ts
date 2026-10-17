import type { SessionView, VersionSummary } from "../api/types";

export type ResultAction = { action: "generate" | "show_result"; label: string; primary: boolean };

export const STALE_NOTICE = "입력이 바뀌어 결과가 최신이 아니에요. 바뀐 내용을 반영하려면 초안을 다시 만들어 주세요.";

export const STALE_BANNER = {
  title: "결과가 최신이 아니에요",
  text: "답변이나 보완 정보가 바뀌었어요. 아래에는 바뀌기 전 결과가 그대로 있어요.",
  action: "바뀐 내용으로 다시 만들기",
};
export const STALE_SAVE_HINT = "바뀐 기준으로 결과를 먼저 다시 만들어 주세요.";

/** [순수] 답변 확인 화면의 결과 버튼. 최신 결과가 있으면 다시 만들기(LLM 호출)보다 보기가 먼저다. */
export function confirmActions(session: Pick<SessionView, "has_result" | "result_stale">): ResultAction[] {
  if (!session.has_result) return [{ action: "generate", label: "맞아요 · 이 정보로 초안 만들기", primary: true }];
  if (session.result_stale) {
    return [
      { action: "generate", label: "바뀐 내용으로 초안 다시 만들기", primary: true },
      { action: "show_result", label: "이전 결과 보기", primary: false },
    ];
  }
  return [
    { action: "show_result", label: "결과 보기", primary: true },
    { action: "generate", label: "초안 다시 만들기", primary: false },
  ];
}

/** 결과 화면 오른쪽의 다시 만들기. 낡은 결과의 다시 만들기는 본문 배너(`STALE_BANNER`)가 맡는다. */
export const REGENERATE_ACTION: ResultAction = { action: "generate", label: "초안 다시 만들기", primary: false };

/** [순수] 버튼 이름과 막힘. 결과 보기는 LLM을 부르지 않으므로 생성 가능 여부와 상관없다. */
export function actionState(
  action: ResultAction,
  busy: boolean,
  canGenerate: boolean,
): { label: string; disabled: boolean } {
  const calls = action.action === "generate";
  return { label: busy && calls ? "초안을 만드는 중…" : action.label, disabled: busy || (calls && !canGenerate) };
}

/** [순수] '현재 버전 저장' 버튼. 저장 전이고 결과가 최신일 때만 주 버튼이고, 이미 저장했거나 결과가 최신이 아니면 막는다. 근거 기록이 있으면 출처와 함께 저장한다고 알린다. */
export function saveButton(
  version: Pick<VersionSummary, "saved">,
  stale: boolean,
  withSources: boolean,
): { label: string; primary: boolean; disabled: boolean } {
  if (version.saved) return { label: "저장한 버전이에요", primary: false, disabled: true };
  const label = withSources ? "출처와 함께 저장" : "현재 버전 저장";
  if (stale) return { label, primary: false, disabled: true };
  return { label, primary: true, disabled: false };
}
