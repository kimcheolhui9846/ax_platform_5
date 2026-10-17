import type { SessionSummary, VersionReason, VersionSummary } from "../api/types";
import type { Route } from "./routes";

const REASON_LABEL: Record<VersionReason, string> = { first: "첫 초안", regenerate: "다시 만든 초안" };

/** "V2 · 다시 만든 초안" */
export function versionLine(version: Pick<VersionSummary, "version" | "reason">): string {
  return `V${version.version} · ${REASON_LABEL[version.reason]}`;
}

/** [순수] 이어서 작업할 화면: 걸린 질문이 있으면 질문, 결과가 있으면 결과, 아니면 답변 확인. */
export function resumeRoute(summary: SessionSummary): Route {
  const sessionId = summary.session_id;
  if (summary.has_question) return { name: "question", sessionId };
  return summary.has_result ? { name: "result", sessionId } : { name: "confirm", sessionId };
}

/** [순수] 목록에 보일 진행 단계. */
export function stageLabel(summary: SessionSummary): string {
  if (summary.has_question) return "질문 진행 중";
  if (!summary.has_result) return "답변 확인";
  const label = `결과 V${summary.latest_version ?? 1}`;
  return summary.result_stale ? `${label} · 최신 아님` : label;
}

/** [순수] 과제마다 가장 최근 세션. 목록은 이미 최근 순이라 처음 나온 것이 가장 최근이다. */
export function latestByTask(sessions: SessionSummary[]): ReadonlyMap<string, SessionSummary> {
  const latest = new Map<string, SessionSummary>();
  for (const summary of sessions) {
    if (!latest.has(summary.task_type)) latest.set(summary.task_type, summary);
  }
  return latest;
}

export type SavedDocument = { session: SessionSummary; version: VersionSummary };

/** [순수] 결과물 목록: 저장한 버전을 최근에 만든 순서로 모은다. */
export function savedDocuments(sessions: SessionSummary[]): SavedDocument[] {
  return sessions
    .flatMap((session) => session.saved_versions.map((version) => ({ session, version })))
    .sort((a, b) => b.version.created_at.localeCompare(a.version.created_at));
}

/** [순수] 목록 제목용으로 긴 글을 줄인다(빈칸은 하나로). */
export function clip(text: string, max = 24): string {
  const flat = text.trim().replace(/\s+/g, " ");
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}
