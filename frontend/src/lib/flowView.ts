import type { FlowItem, FlowStatus, Question } from "../api/types";

/** 답을 고칠 수 있는 흐름 항목: 답했거나 미정으로 둔 질문(그 질문이 실려 있다). */
export type EditableFlowItem = FlowItem & { question: Question };

export function isEditable(item: FlowItem): item is EditableFlowItem {
  return item.question !== null && (item.status === "answered" || item.status === "skipped");
}

const STATUS_LABEL: Record<FlowStatus, string> = {
  answered: "완료",
  current: "현재 질문",
  upcoming: "예정",
  skipped: "아직 미정",
};

export function flowStatusLabel(status: FlowStatus): string {
  return STATUS_LABEL[status];
}

/** 흐름 패널 번호. 01은 요청 정리라 질문은 02부터다. */
export function flowNumber(index: number): string {
  return String(index + 2).padStart(2, "0");
}

/** 항목 아래 한 줄: 정한 답이나 지금 상태. */
export function flowNote(item: FlowItem): string {
  switch (item.status) {
    case "answered":
      return item.answer ?? "";
    case "skipped":
      return "아직 미정으로 남겨 뒀어요.";
    case "current":
      return "답변을 기다리고 있어요.";
    case "upcoming":
      return "차례가 오면 물어볼게요.";
  }
}

/** '← 이전 단계'로 고칠 질문: 지금 질문 바로 앞(지금 질문이 없으면 마지막)의 답한·미정 항목. */
export function previousEditable(flow: FlowItem[]): string | null {
  const current = flow.findIndex((item) => item.status === "current");
  const before = current === -1 ? flow : flow.slice(0, current);
  const item = [...before].reverse().find(isEditable);
  return item ? item.question.question_id : null;
}

/** '답변 바꾸기'로 고칠 첫 질문. */
export function firstEditable(flow: FlowItem[]): string | null {
  const item = flow.find(isEditable);
  return item ? item.question.question_id : null;
}

/** 진행 표시. 물어본(답한·미정) 질문과 지금 질문을 세고, 지금 질문이 없으면 마쳤다고 붙인다. */
export function questionPosition(flow: FlowItem[], cap: number): string {
  const shown = Math.min(flow.filter((item) => item.status !== "upcoming").length, cap);
  return flow.some((item) => item.status === "current") ? `질문 ${shown}/${cap}` : `질문 ${shown}/${cap} · 마침`;
}
