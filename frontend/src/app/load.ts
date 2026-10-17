import { isListRoute, sessionIdOf, taskOf } from "../lib/routes";
import type { AppState } from "./state";

/** 화면을 그리는 데 모자란 데이터 하나. */
export type Load =
  | { kind: "tasks" }
  | { kind: "sessions" }
  | { kind: "form"; task: string }
  | { kind: "session"; sessionId: string }
  | { kind: "result"; sessionId: string }
  | { kind: "evidence"; sessionId: string }
  | { kind: "version"; sessionId: string; version: number };

export function loadKey(load: Load): string {
  switch (load.kind) {
    case "tasks":
    case "sessions":
      return load.kind;
    case "form":
      return `form:${load.task}`;
    case "version":
      return `version:${load.sessionId}:${load.version}`;
    default:
      return `${load.kind}:${load.sessionId}`;
  }
}

/** [순수] 지금 불러올 데이터. 요청을 기다리는 중이거나 같은 불러오기가 이 화면에서 실패했으면 부르지 않는다. */
export function needsLoad(state: AppState): Load | null {
  if (state.inflight !== null) return null;
  const load = missing(state);
  return load !== null && loadKey(load) !== state.stalled ? load : null;
}

function missing(state: AppState): Load | null {
  const { route } = state;
  if (state.tasks === null) return { kind: "tasks" };
  if (isListRoute(route)) return state.sessions === null ? { kind: "sessions" } : null;
  const task = taskOf(route);
  if (task !== null) return state.form?.task_type === task ? null : { kind: "form", task };
  const sessionId = sessionIdOf(route);
  if (sessionId === null) return null;
  const session = state.session;
  if (session === null || session.session_id !== sessionId || state.sessionOutdated) {
    return { kind: "session", sessionId };
  }
  if (route.name === "version" || route.name === "saved") {
    const version = state.version;
    const loaded = version !== null && version.session_id === sessionId && version.version.version === route.version;
    return loaded ? null : { kind: "version", sessionId, version: route.version };
  }
  // 결과 화면·문구 수정·근거 검토는 결과까지 있어야 그린다
  const wantsResult = (route.name === "result" || route.name === "edit" || route.name === "evidence") && session.has_result;
  if (wantsResult && state.result?.session_id !== sessionId) return { kind: "result", sessionId };
  if (route.name === "evidence" && session.has_result && state.evidence?.sessionId !== sessionId) return { kind: "evidence", sessionId };
  return null;
}
