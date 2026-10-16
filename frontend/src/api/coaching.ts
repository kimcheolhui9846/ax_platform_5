import { api } from "./client";
import type { ApiResult } from "./client";
import type {
  AnswerBody,
  CoachingMode,
  ResultView,
  ReviseBody,
  SessionView,
  TaskForm,
  TaskSummary,
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
