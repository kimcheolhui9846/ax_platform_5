import type { EvidenceItem, EvidenceRecord, VersionReason, VersionSummary } from "../api/types";
import { cardLabel } from "./labels";

export const EVIDENCE_APPLIED_NOTICE = "점검 항목과 출처를 반영했어요.";

/** [순수] 링크로 쓸 수 있는 원문 주소(http·https만). 아니면 null이라 링크를 그리지 않는다. */
export function safeUrl(url: string): string | null {
  const trimmed = url.trim();
  return /^https?:\/\//i.test(trimmed) ? trimmed : null;
}

/** [순수] 결과에 이미 반영한 자료 id. */
export function appliedSourceIds(evidence: EvidenceRecord[]): Set<string> {
  return new Set(evidence.map((record) => record.source_id));
}

/** [순수] 결과 화면의 근거 버튼. 자료가 없는 과제는 없고, 반영한 뒤에는 다시 보기(주 버튼 아님)다. */
export function evidenceButton(count: number, applied: boolean): { label: string; primary: boolean } | null {
  if (count === 0) return null;
  return applied ? { label: "근거 자료 다시 보기", primary: false } : { label: `근거 자료 검토 · ${count}건`, primary: true };
}

/** [순수] '근거 반영 전 보기'가 열 버전(근거를 반영한 버전의 바로 앞). 아니면 null. */
export function versionBeforeEvidence(version: Pick<VersionSummary, "version" | "reason">): number | null {
  return version.reason === "evidence" && version.version > 1 ? version.version - 1 : null;
}

/** [순수] 결과 화면 오른쪽 패널 제목. */
export function resultHeading(reason: VersionReason): string {
  return reason === "evidence" ? "검토 내용을 반영했어요" : "결과를 확인해 주세요";
}

/** [순수] 근거 검토 화면에서 반영할 내용 이름: "제안 · 제작 점검 항목". */
export function proposalLabel(item: Pick<EvidenceItem, "applies_to" | "record">): string {
  return `${cardLabel(item.applies_to)} · ${item.record?.title ?? ""}`;
}
