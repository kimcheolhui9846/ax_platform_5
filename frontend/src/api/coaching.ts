import { api } from "./client";
import type { ApiResult } from "./client";
import type {
  AnswerBody,
  CoachingMode,
  ResultView,
  ReviseBody,
  SessionSummary,
  SessionView,
  TaskForm,
  TaskSummary,
  VersionView,
} from "./types";

export type { ApiResult } from "./client";

const BASE = "/api/v1/coaching";

export function listTasks(): Promise<ApiResult<TaskSummary[]>> {
  return api.GET(`${BASE}/tasks`);
}

export function getTaskForm(taskType: string): Promise<ApiResult<TaskForm>> {
  return api.GET(`${BASE}/tasks/{task_type}/form`, {
    params: { path: { task_type: taskType } },
  });
}

export function createSession(
  taskType: string,
  rawInput: string,
  mode: CoachingMode = "standard",
): Promise<ApiResult<SessionView>> {
  return api.POST(`${BASE}/tasks/{task_type}/sessions`, {
    params: { path: { task_type: taskType } },
    body: { raw_input: rawInput, mode },
  });
}

/** 내 세션 요약(최근에 바뀐 순서). 내 작업·결과물·홈 이어하기가 쓴다. */
export function listSessions(): Promise<ApiResult<SessionSummary[]>> {
  return api.GET(`${BASE}/sessions`);
}

export function getSession(sessionId: string): Promise<ApiResult<SessionView>> {
  return api.GET(`${BASE}/sessions/{session_id}`, {
    params: { path: { session_id: sessionId } },
  });
}

export function submitAnswer(
  sessionId: string,
  questionId: string,
  body: AnswerBody,
): Promise<ApiResult<SessionView>> {
  return api.POST(`${BASE}/sessions/{session_id}/answers`, {
    params: { path: { session_id: sessionId } },
    body: { ...body, question_id: questionId },
  });
}

export function reviseAnswer(
  sessionId: string,
  questionId: string,
  body: ReviseBody,
): Promise<ApiResult<SessionView>> {
  return api.PATCH(`${BASE}/sessions/{session_id}/answers/{question_id}`, {
    params: { path: { session_id: sessionId, question_id: questionId } },
    body,
  });
}

/** 결과를 만든 뒤 질문을 이어 간다. 남은 질문이 있으면 next_question에 걸려 돌아온다. */
export function continueSession(sessionId: string): Promise<ApiResult<SessionView>> {
  return api.POST(`${BASE}/sessions/{session_id}/continue`, {
    params: { path: { session_id: sessionId } },
  });
}

/** '원래 예시 보기'. 사다리 질문을 기본 질문으로 되돌린다(LLM 호출 없음). */
export function showOriginalQuestion(sessionId: string): Promise<ApiResult<SessionView>> {
  return api.POST(`${BASE}/sessions/{session_id}/question/original`, {
    params: { path: { session_id: sessionId } },
  });
}

export function generateResult(sessionId: string): Promise<ApiResult<ResultView>> {
  return api.POST(`${BASE}/sessions/{session_id}/generate`, {
    params: { path: { session_id: sessionId } },
  });
}

export function getResult(sessionId: string): Promise<ApiResult<ResultView>> {
  return api.GET(`${BASE}/sessions/{session_id}/result`, {
    params: { path: { session_id: sessionId } },
  });
}

/** 버전 하나 보기(보기 전용). */
export function getVersion(sessionId: string, version: number): Promise<ApiResult<VersionView>> {
  return api.GET(`${BASE}/sessions/{session_id}/versions/{version}`, {
    params: { path: { session_id: sessionId, version } },
  });
}

/** 그 버전에 저장 표시를 한다. */
export function saveVersion(sessionId: string, version: number): Promise<ApiResult<VersionView>> {
  return api.POST(`${BASE}/sessions/{session_id}/versions/{version}/save`, {
    params: { path: { session_id: sessionId, version } },
  });
}
