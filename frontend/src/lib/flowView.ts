import type { FlowItem, Question } from "../api/types";

/** 답을 고칠 수 있는 흐름 항목: 답했거나 미정으로 둔 질문(그 질문이 실려 있다). */
export type EditableFlowItem = FlowItem & { question: Question };

export function isEditable(item: FlowItem): item is EditableFlowItem {
  return item.question !== null && (item.status === "answered" || item.status === "skipped");
}
