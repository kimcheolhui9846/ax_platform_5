import type { SummaryItem, UnknownItem } from "../api/types";

export type CriteriaRow = { field: string; label: string; value: string; note: string | null };

/** [순수] '내 답변에서 반영한 기준'. 확인한 값(출처)과 AI 가정(확인 필요)을 정책 순서로, 그 뒤에 아직 미정. */
export function criteriaRows(summary: SummaryItem[], unknowns: UnknownItem[]): CriteriaRow[] {
  return [
    ...summary.map((item) => ({
      field: item.field,
      label: item.label,
      value: item.value,
      note: item.is_assumption ? "AI 가정 · 확인 필요" : item.source_label,
    })),
    ...unknowns.map((item) => ({ field: item.field, label: item.label, value: "아직 미정", note: null })),
  ];
}
