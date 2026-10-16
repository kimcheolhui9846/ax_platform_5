import { api } from "./client";
import type { AnswerBody, CoachingMode, ResultView, SessionView, TaskSummary } from "./types";

/**
 * openapi-fetch 응답 중 화면이 쓰는 부분. 백엔드 오류 본문은 계약상 ErrorBody({detail})지만
 * 개발 프록시·게이트웨이 오류처럼 계약 밖 본문도 올 수 있어 error는 unknown으로 받고 errorMessage가 거른다.
 */
export type ApiResult<T> = { data?: T; error?: unknown };

const BASE = "/api/v1/coaching";

export function listTasks(): Promise<ApiResult<TaskSummary[]>> {
  return api.GET(`${BASE}/tasks`);
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

export function generateResult(sessionId: string): Promise<ApiResult<ResultView>> {
  return api.POST(`${BASE}/sessions/{session_id}/generate`, {
    params: { path: { session_id: sessionId } },
  });
}
