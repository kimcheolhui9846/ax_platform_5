import { blobToDataUrl } from "../lib/dataUrl";
import type { CarrySource } from "../lib/carry";
import { api } from "./client";
import type { ApiResult } from "./client";
import type {
  AnswerBody,
  CoachingMode,
  EvidenceItem,
  ResultView,
  ReviseBody,
  SessionContext,
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
  mode: CoachingMode,
  from: CarrySource | null,
  noticeAcknowledged: boolean,
): Promise<ApiResult<SessionView>> {
  return api.POST(`${BASE}/tasks/{task_type}/sessions`, {
    params: { path: { task_type: taskType } },
    body: {
      raw_input: rawInput,
      mode,
      notice_acknowledged: noticeAcknowledged,
      ...(from ? { from_session_id: from.sessionId, from_version: from.version } : {}),
    },
  });
}

/** 이어 갈 이전 작업의 한 버전에서 새 과제로 가져올 내용 미리보기. */
export function previewContext(taskType: string, sessionId: string, version: number): Promise<ApiResult<SessionContext>> {
  return api.GET(`${BASE}/tasks/{task_type}/context`, {
    params: { path: { task_type: taskType }, query: { session_id: sessionId, version } },
  });
}

/** 세션에 가져온 내용을 뺀다. */
export function clearContext(sessionId: string): Promise<ApiResult<SessionView>> {
  return api.DELETE(`${BASE}/sessions/{session_id}/context`, {
    params: { path: { session_id: sessionId } },
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

/** 미확인 정보를 저장한다(사용자 입력·검증 전). null이면 그 항목을 지운다. */
export function saveSupplements(
  sessionId: string,
  values: Record<string, string | null>,
  privacy: Record<string, boolean>,
): Promise<ApiResult<SessionView>> {
  return api.PUT(`${BASE}/sessions/{session_id}/supplements`, {
    params: { path: { session_id: sessionId } },
    body: { values, private: privacy },
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

/** 결과 섹션 하나의 문구를 고친 새 버전을 만든다(LLM 호출 없음). */
export function editResultSection(sessionId: string, order: number, text: string): Promise<ApiResult<ResultView>> {
  return api.PATCH(`${BASE}/sessions/{session_id}/result/sections/{order}`, {
    params: { path: { session_id: sessionId, order } },
    body: { text },
  });
}

/** 그 버전에 저장 표시를 한다. */
export function saveVersion(sessionId: string, version: number): Promise<ApiResult<VersionView>> {
  return api.POST(`${BASE}/sessions/{session_id}/versions/{version}/save`, {
    params: { path: { session_id: sessionId, version } },
  });
}

/** 작업(세션)을 통째로 지운다. 응답 본문은 없다(204). */
export function deleteSession(sessionId: string): Promise<ApiResult<void>> {
  return api.DELETE(`${BASE}/sessions/{session_id}`, {
    params: { path: { session_id: sessionId } },
  });
}

/** 작업 이름을 바꾼다. */
export function renameSession(sessionId: string, name: string): Promise<ApiResult<SessionSummary>> {
  return api.PATCH(`${BASE}/sessions/{session_id}`, {
    params: { path: { session_id: sessionId } },
    body: { name },
  });
}

/** 그 버전의 저장 표시를 지운다(결과물에서 뺀다). */
export function unsaveVersion(sessionId: string, version: number): Promise<ApiResult<SessionSummary>> {
  return api.DELETE(`${BASE}/sessions/{session_id}/versions/{version}/save`, {
    params: { path: { session_id: sessionId, version } },
  });
}

/** 결과를 검토할 근거 자료(지금은 샘플). */
export function getEvidence(sessionId: string): Promise<ApiResult<EvidenceItem[]>> {
  return api.GET(`${BASE}/sessions/{session_id}/evidence`, {
    params: { path: { session_id: sessionId } },
  });
}

/** 근거 자료의 점검 문구와 출처를 결과에 붙인 새 버전을 만든다(LLM 호출 없음). */
export function applyEvidence(sessionId: string, sourceId: string): Promise<ApiResult<ResultView>> {
  return api.POST(`${BASE}/sessions/{session_id}/evidence/{source_id}/apply`, {
    params: { path: { session_id: sessionId, source_id: sourceId } },
  });
}

/** 결과 이미지 하나. 브라우저 <img>는 사용자 헤더를 못 보내서 헤더를 붙여 받아 data URL로 돌려준다. */
export async function getAsset(assetId: string): Promise<ApiResult<string>> {
  const { data, error, response } = await api.GET(`${BASE}/assets/{asset_id}`, {
    params: { path: { asset_id: assetId } },
    parseAs: "blob",
  });
  return { data: data instanceof Blob ? await blobToDataUrl(data) : undefined, error, response };
}
