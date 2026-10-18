import { beforeEach, describe, expect, expectTypeOf, it, vi } from "vitest";

vi.mock("./client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

import { api } from "./client";
import type { ApiResult } from "./coaching";
import {
  applyEvidence,
  continueSession,
  clearContext,
  createSession,
  editResultSection,
  generateResult,
  getAsset,
  getEvidence,
  getResult,
  getVersion,
  listSessions,
  previewContext,
  saveVersion,
  getSession,
  getTaskForm,
  listTasks,
  reviseAnswer,
  saveSupplements,
  showOriginalQuestion,
  submitAnswer,
} from "./coaching";
import type { ResultView, SessionSummary, SessionView, TaskForm, TaskSummary, VersionView } from "./types";

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
    await createSession("branding", "향초", "standard", null, true);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/tasks/{task_type}/sessions`, {
      params: { path: { task_type: "branding" } },
      body: { raw_input: "향초", mode: "standard", notice_acknowledged: true },
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

  it("답변·수정은 비공개 표시를 그대로 싣는다", async () => {
    await submitAnswer("sess_1", "q_1", { answer_type: "free_text", value: "9900", private: true });
    expect(api.POST).toHaveBeenLastCalledWith(`${BASE}/sessions/{session_id}/answers`, {
      params: { path: { session_id: "sess_1" } },
      body: { answer_type: "free_text", value: "9900", private: true, question_id: "q_1" },
    });
    await reviseAnswer("sess_1", "q_1", { answer_type: "free_text", value: "1", private: false });
    expect(api.PATCH).toHaveBeenLastCalledWith(`${BASE}/sessions/{session_id}/answers/{question_id}`, {
      params: { path: { session_id: "sess_1", question_id: "q_1" } },
      body: { answer_type: "free_text", value: "1", private: false },
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

  it("내 세션 목록·버전 보기·저장", async () => {
    await listSessions();
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/sessions`);

    await getVersion("sess_1", 2);
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/versions/{version}`, {
      params: { path: { session_id: "sess_1", version: 2 } },
    });

    await saveVersion("sess_1", 2);
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/versions/{version}/save`, {
      params: { path: { session_id: "sess_1", version: 2 } },
    });

    expectTypeOf(listSessions).returns.resolves.toEqualTypeOf<ApiResult<SessionSummary[]>>();
    expectTypeOf(getVersion).returns.resolves.toEqualTypeOf<ApiResult<VersionView>>();
    expectTypeOf(saveVersion).returns.resolves.toEqualTypeOf<ApiResult<VersionView>>();
  });

  it("결과 문구 수정", async () => {
    await editResultSection("sess_1", 1, "고친 문구");
    expect(api.PATCH).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/result/sections/{order}`, {
      params: { path: { session_id: "sess_1", order: 1 } },
      body: { text: "고친 문구" },
    });
    expectTypeOf(editResultSection).returns.resolves.toEqualTypeOf<ApiResult<ResultView>>();
  });

  it("미확인 정보 저장", async () => {
    await saveSupplements("sess_1", { material: "면", size: null }, { sale_price: false });
    expect(api.PUT).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/supplements`, {
      params: { path: { session_id: "sess_1" } },
      body: { values: { material: "면", size: null }, private: { sale_price: false } },
    });
    expectTypeOf(saveSupplements).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
  });

  it("근거 자료 목록과 반영", async () => {
    await getEvidence("s1");
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/evidence`, {
      params: { path: { session_id: "s1" } },
    });
    await applyEvidence("s1", "zip");
    expect(api.POST).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/evidence/{source_id}/apply`, {
      params: { path: { session_id: "s1", source_id: "zip" } },
    });
  });

  it("이미지는 헤더를 붙여 받아 data URL로 돌려준다", async () => {
    const response = new Response(null, { status: 200 });
    vi.mocked(api.GET).mockResolvedValueOnce({ data: new Blob(["<svg/>"], { type: "image/svg+xml" }), response } as never);
    const result = await getAsset("asset_a");
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/assets/{asset_id}`, { params: { path: { asset_id: "asset_a" } }, parseAs: "blob" });
    expect(result.data).toBe("data:image/svg+xml;base64,PHN2Zy8+");
  });

  it("이미지를 못 받으면 데이터 없이 오류를 전한다", async () => {
    const response = new Response(null, { status: 404 });
    vi.mocked(api.GET).mockResolvedValueOnce({ error: { detail: "없는 이미지예요." }, response } as never);
    const result = await getAsset("nope");
    expect(result.data).toBeUndefined();
    expect(result.error).toEqual({ detail: "없는 이미지예요." });
  });

  it("돌려주는 타입", () => {
    expectTypeOf(listTasks).returns.resolves.toEqualTypeOf<ApiResult<TaskSummary[]>>();
    expectTypeOf(getTaskForm).returns.resolves.toEqualTypeOf<ApiResult<TaskForm>>();
    expectTypeOf(getSession).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
    expectTypeOf(reviseAnswer).returns.resolves.toEqualTypeOf<ApiResult<SessionView>>();
    expectTypeOf(getResult).returns.resolves.toEqualTypeOf<ApiResult<ResultView>>();
  });
});

describe("이어가기", () => {
  it("createSession은 출처가 있을 때만 본문에 싣는다", async () => {
    await createSession("branding", "글", "standard", { sessionId: "s1", version: 2 }, true);
    expect(api.POST).toHaveBeenLastCalledWith(`${BASE}/tasks/{task_type}/sessions`, {
      params: { path: { task_type: "branding" } },
      body: { raw_input: "글", mode: "standard", notice_acknowledged: true, from_session_id: "s1", from_version: 2 },
    });
    await createSession("branding", "글", "standard", null, true);
    expect(api.POST).toHaveBeenLastCalledWith(`${BASE}/tasks/{task_type}/sessions`, {
      params: { path: { task_type: "branding" } },
      body: { raw_input: "글", mode: "standard", notice_acknowledged: true },
    });
  });

  it("미리보기와 빼기", async () => {
    await previewContext("branding", "s1", 2);
    expect(api.GET).toHaveBeenCalledWith(`${BASE}/tasks/{task_type}/context`, {
      params: { path: { task_type: "branding" }, query: { session_id: "s1", version: 2 } },
    });
    await clearContext("s1");
    expect(api.DELETE).toHaveBeenCalledWith(`${BASE}/sessions/{session_id}/context`, {
      params: { path: { session_id: "s1" } },
    });
  });
});
