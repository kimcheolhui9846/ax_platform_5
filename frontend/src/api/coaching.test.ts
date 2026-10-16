import { beforeEach, describe, expect, expectTypeOf, it, vi } from "vitest";

vi.mock("./client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn() } }));

import { api } from "./client";
import type { ApiResult } from "./coaching";
import {
  continueSession,
  createSession,
  generateResult,
  getResult,
  getSession,
  getTaskForm,
  listTasks,
  reviseAnswer,
  showOriginalQuestion,
  submitAnswer,
} from "./coaching";
import type { ResultView, SessionView, TaskForm, TaskSummary } from "./types";

const BASE = "/api/v1/coaching";

beforeEach(() => vi.clearAllMocks());

describe("coaching API 래퍼", () => {
  it("과제 목록·입력 양식", async () => {
    await listTasks();
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/tasks`);

    await getTaskForm("branding");
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/tasks/{task_type}/form`, {
      params: { path: { task_type: "branding" } },
    });
  });

  it("세션 만들기·조회", async () => {
    await createSession("branding", "향초");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/tasks/{task_type}/sessions`, {
      params: { path: { task_type: "branding" } },
      body: { raw_input: "향초", mode: "standard" },
    });

    await getSession("sess_1");
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}`, {
      params: { path: { session_id: "sess_1" } },
    });
  });

  it("답변·수정", async () => {
    await submitAnswer("sess_1", "q_1", { answer_type: "skip" });
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/answers`, {
      params: { path: { session_id: "sess_1" } },
      body: { answer_type: "skip", question_id: "q_1" },
    });

    await reviseAnswer("sess_1", "q_1", { answer_type: "free_text", value: "부모" });
    expect(api.PATCH).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/answers/{question_id}`, {
      params: { path: { session_id: "sess_1", question_id: "q_1" } },
      body: { answer_type: "free_text", value: "부모" },
    });
  });

  it("결과 뒤 질문 이어 가기", async () => {
    await continueSession("sess_1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/continue`, {
      params: { path: { session_id: "sess_1" } },
    });
    expectTypeOf(continueSession).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
  });

  it("원래 예시 보기", async () => {
    await showOriginalQuestion("sess_1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/question/original`, {
      params: { path: { session_id: "sess_1" } },
    });
    expectTypeOf(showOriginalQuestion).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
  });

  it("결과 만들기·조회", async () => {
    await generateResult("sess_1");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/generate`, {
      params: { path: { session_id: "sess_1" } },
    });

    await getResult("sess_1");
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/result`, {
      params: { path: { session_id: "sess_1" } },
    });
  });

  it("돌려주는 타입", () => {
    expectTypeOf(listTasks).returns.resolves.toEqualTypeOf<ApiResult<TaskSummary[]>>();
    expectTypeOf(getTaskForm).returns.resolves.toEqualTypeOf<ApiResult<TaskForm>>();
    expectTypeOf(getSession).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
    expectTypeOf(reviseAnswer).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
    expectTypeOf(getResult).returns.resolves.toEqualTypeOf<ApiResult<ResultView>>();
  });
});
