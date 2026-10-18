import type { SupplementItem } from "../api/types";

/** 미확인 정보 패널에 보일 것. canApply는 '초안에 반영'을 누를 수 있는지다. */
export type SupplementStatus = { line: string; missing: string; canApply: boolean };

/** 결과 문서에 실을 반영된 보완 정보 한 줄. */
export type AppliedRow = { label: string; value: string; private: boolean }; // private: 그 결과를 만들 때 AI에 보내지 않은 항목

export const ALL_FILLED_NOTE = "모든 항목에 입력값이 있어요. 사실 검증 완료를 의미하지 않아요.";

const filled = (items: SupplementItem[]) => items.filter((item) => item.value !== null);

/**
 * [순수] 미확인 정보 패널 문구. current는 지금 입력(세션), applied는 지금 결과에 반영한 값(결과),
 * changed는 입력이 아직 결과에 반영되지 않았는지(서버가 정한 SessionView.supplements_changed),
 * canGenerate는 지금 초안을 만들 수 있는지(SessionView.can_generate)다. 반영은 생성이라 둘 다 참일 때만 누를 수 있다.
 */
export function supplementStatus(
  current: SupplementItem[],
  applied: SupplementItem[],
  changed: boolean,
  canGenerate: boolean,
): SupplementStatus {
  const state = changed ? "아직 초안에 미반영" : filled(applied).length > 0 ? "초안에 반영됨" : "보완할 정보를 입력해 주세요";
  const missing = current.filter((item) => item.value === null).map((item) => item.label);
  return {
    line: `입력 ${filled(current).length}/${current.length} · ${state}`,
    missing: missing.length > 0 ? `미확인: ${missing.join(" · ")}` : ALL_FILLED_NOTE,
    canApply: changed && canGenerate,
  };
}

/** [순수] 대화상자 입력의 처음 값(항목 이름 → 글). 미확인은 빈 글이다. */
export function supplementDraft(items: SupplementItem[]): Record<string, string> {
  return Object.fromEntries(items.map((item) => [item.name, item.value ?? ""]));
}

/** [순수] 저장할 값. 앞뒤 공백을 지우고, 빈 글은 미확인(null)이다. */
export function supplementValues(draft: Record<string, string>): Record<string, string | null> {
  return Object.fromEntries(Object.entries(draft).map(([name, text]) => [name, text.trim() === "" ? null : text.trim()]));
}

/** [순수] 결과 문서에 실을 보완 정보. 반영한 값이 하나도 없으면 빈 목록이다(문서에 칸을 두지 않는다). */
export function appliedRows(applied: SupplementItem[]): AppliedRow[] {
  if (filled(applied).length === 0) return [];
  return applied.map((item) => ({ label: item.label, value: item.value ?? "미확인", private: item.private }));
}

/** 보완 대화상자의 단계: 닫힘 · 열림 · 저장 중(연 채 요청을 기다린다). */
export type PanelPhase = "closed" | "open" | "saving";

/** 대화상자에 일어난 일. settled는 저장 요청이 끝났다는 신호이고 saved는 입력이 실제로 저장됐는지다. */
export type PanelEvent = { type: "open" } | { type: "cancel" } | { type: "save" } | { type: "settled"; saved: boolean };

/**
 * [순수] 대화상자의 다음 단계. 저장하면 연 채 저장 중이 되고, 끝났을 때 성공이면 닫고 실패면 연 채 입력을 살린다.
 * 저장 중에는 취소·재저장을 받지 않고, 저장 중이 아닐 때 온 settled는 무시한다.
 */
export function panelAfter(phase: PanelPhase, event: PanelEvent): PanelPhase {
  switch (phase) {
    case "closed":
      return event.type === "open" ? "open" : "closed";
    case "open":
      if (event.type === "cancel") return "closed";
      return event.type === "save" ? "saving" : "open";
    case "saving":
      if (event.type !== "settled") return "saving";
      return event.saved ? "closed" : "open";
  }
}
