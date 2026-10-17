import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/coaching", () => ({
  createSession: vi.fn(),
  submitAnswer: vi.fn(),
  reviseAnswer: vi.fn(),
  generateResult: vi.fn(),
  continueSession: vi.fn(),
  showOriginalQuestion: vi.fn(),
  saveVersion: vi.fn(),
  saveSupplements: vi.fn(),
  editResultSection: vi.fn(),
}));

import { continueSession, createSession, editResultSection, generateResult, reviseAnswer, saveSupplements, saveVersion, showOriginalQuestion, submitAnswer } from "../api/coaching";
import { HOME } from "../lib/routes";
import type { DocumentFile } from "../lib/documentHtml";
import { makeQuestion, makeResult, makeSession, makeSessionSummary, makeVersionView } from "../testing/factories";
import { DOWNLOADED_NOTICE, NOTHING_LEFT_NOTICE, SECTION_EDITED_NOTICE, SUPPLEMENTS_APPLIED_NOTICE, SUPPLEMENTS_SAVED_NOTICE, makeHandlers, routeAfterSession } from "./handlers";
import type { Call, Runner } from "./requests";
import { initialState } from "./state";
import type { Action, AppState } from "./state";

beforeEach(() => vi.clearAllMocks());

function setup(patch: Partial<AppState> = {}) {
  const calls: Call<unknown>[] = [];
  const actions: Action[] = [];
  const saved: [string, string][] = [];
  const files: DocumentFile[] = [];
  const run: Runner = async <T>(call: Call<T>) => {
    calls.push(call as unknown as Call<unknown>);
  };
  const on = makeHandlers({
    state: { ...initialState(HOME), ...patch },
    run,
    dispatch: (action) => actions.push(action),
    saveDraft: (task, text) => saved.push([task, text]),
    saveFile: (file) => files.push(file),
  });
  return { on, calls, actions, saved, files };
}

const session = makeSession({ session_id: "sess_1", next_question: makeQuestion({ question_id: "q_1" }) });

describe("routeAfterSession", () => {
  it("걸린 질문이 있으면 질문, 없으면 답변 확인", () => {
    expect(routeAfterSession(session)).toEqual({ name: "question", sessionId: "sess_1" });
    expect(routeAfterSession(makeSession({ next_question: null }))).toEqual({ name: "confirm", sessionId: "sess_1" });
  });
});

describe("makeHandlers — 이동", () => {
  it("과제 화면 이동", () => {
    const { on, actions } = setup();
    on.start("branding");
    on.submitRequest("branding");
    on.editRequest("branding");
    on.guide();
    on.goHome();
    on.navigate("home");
    on.retry();
    expect(actions).toEqual([
      { type: "navigated", route: { name: "request", task: "branding" } },
      { type: "navigated", route: { name: "mode", task: "branding" } },
      { type: "navigated", route: { name: "request", task: "branding" } },
      { type: "navigated", route: { name: "guide" } },
      { type: "navigated", route: HOME },
      { type: "navigated", route: HOME },
      { type: "retried" },
    ]);
  });

  it("세션 화면 이동", () => {
    const { on, actions } = setup({ session });
    on.edit("q_0");
    on.earlyDraft();
    on.backToQuestions();
    on.showResult();
    on.confirm();
    expect(actions.map((a) => (a.type === "navigated" ? a.route : a))).toEqual([
      { name: "revise", sessionId: "sess_1", questionId: "q_0" },
      { name: "confirm", sessionId: "sess_1" },
      { name: "question", sessionId: "sess_1" },
      { name: "result", sessionId: "sess_1" },
      { name: "confirm", sessionId: "sess_1" },
    ]);
  });

  it("쓰다 만 요청 글은 상태와 저장소에 함께 둔다", () => {
    const { on, actions, saved } = setup();
    on.changeDraft("branding", "한글 파우치");
    expect(actions).toEqual([{ type: "draftChanged", task: "branding", text: "한글 파우치" }]);
    expect(saved).toEqual([["branding", "한글 파우치"]]);
  });

  it("세션이 없으면 세션 동작은 아무것도 하지 않는다", () => {
    const { on, calls, actions } = setup();
    on.answer({ answer_type: "skip" });
    on.generate();
    on.earlyDraft();
    expect([calls, actions]).toEqual([[], []]);
  });
});

describe("makeHandlers — 요청", () => {
  it("모드를 고르면 쓰다 만 요청 글로 세션을 만들고 첫 질문으로 간다", async () => {
    const { on, calls } = setup({ drafts: { branding: "한글 파우치" } });
    on.pickMode("branding", "precise");
    await calls[0].request();
    expect(createSession).toHaveBeenCalledWith("branding", "한글 파우치", "precise");
    expect(calls[0].done(session, 3)).toEqual({
      type: "sessionLoaded",
      seq: 3,
      session,
      next: { name: "question", sessionId: "sess_1" },
      notice: null,
    });
  });

  it("답하기·다른 예시·원래 예시·고치기는 바뀐 세션의 다음 화면으로 간다", async () => {
    const { on, calls } = setup({ session });
    on.answer({ answer_type: "option", option_ids: ["o1"] });
    on.example("easier");
    on.example("original");
    on.revise("q_0", { answer_type: "free_text", value: "부모" });
    for (const call of calls) await call.request();

    expect(submitAnswer).toHaveBeenNthCalledWith(1, "sess_1", "q_1", { answer_type: "option", option_ids: ["o1"] });
    expect(submitAnswer).toHaveBeenNthCalledWith(2, "sess_1", "q_1", { answer_type: "easier" });
    expect(showOriginalQuestion).toHaveBeenCalledWith("sess_1");
    expect(reviseAnswer).toHaveBeenCalledWith("sess_1", "q_0", { answer_type: "free_text", value: "부모" });

    const done = makeSession({ next_question: null });
    for (const call of calls) {
      expect(call.done(done, 1)).toMatchObject({ type: "sessionLoaded", next: { name: "confirm", sessionId: "sess_1" } });
      expect(call.load).toBeNull();
      expect(call.outdatesSessionOnFail).toBe(false);
    }
  });

  it("초안 만들기는 결과 화면으로 가고, 성공이든 실패든 세션을 다시 받는다", async () => {
    const { on, calls } = setup({ session });
    on.generate();
    await calls[0].request();
    expect(generateResult).toHaveBeenCalledWith("sess_1");
    expect(calls[0].outdatesSessionOnFail).toBe(true);
    expect(calls[0].done(makeResult(), 5)).toEqual({
      type: "resultLoaded",
      seq: 5,
      result: makeResult(),
      next: { name: "result", sessionId: "sess_1" },
      outdatesSession: true,
      notice: null,
    });
  });

  it("질문 이어 가기는 남은 질문이 있으면 질문으로, 없으면 알림만", async () => {
    const { on, calls } = setup({ session });
    on.continueQuestions();
    await calls[0].request();
    expect(continueSession).toHaveBeenCalledWith("sess_1");
    expect(calls[0].done(session, 1)).toEqual({
      type: "sessionLoaded",
      seq: 1,
      session,
      next: { name: "question", sessionId: "sess_1" },
      notice: null,
    });
    const nothing = makeSession({ next_question: null });
    expect(calls[0].done(nothing, 2)).toEqual({ type: "sessionLoaded", seq: 2, session: nothing, next: null, notice: NOTHING_LEFT_NOTICE });
  });

  it("왼쪽 메뉴는 홈·내 작업·결과물을 연다", () => {
    const { on, actions } = setup();
    on.navigate("home");
    on.navigate("work");
    on.navigate("documents");
    expect(actions.map((a) => (a.type === "navigated" ? a.route : a))).toEqual([HOME, { name: "work" }, { name: "documents" }]);
  });

  it("이어하기는 세션의 진행 단계로, 버전 열기는 버전 보기로 간다", () => {
    const { on, actions } = setup();
    on.resume(makeSessionSummary({ has_question: false, has_result: true }));
    on.openVersion("sess_9", 3);
    expect(actions.map((a) => (a.type === "navigated" ? a.route : a))).toEqual([
      { name: "result", sessionId: "sess_1" },
      { name: "version", sessionId: "sess_9", version: 3 },
    ]);
  });

  it("현재 버전 저장은 지금 결과의 버전을 저장하고 저장 완료로 간다", async () => {
    const result = makeResult({ version: { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: false } });
    const { on, calls } = setup({ session, result });
    on.saveVersion();
    await calls[0].request();
    expect(saveVersion).toHaveBeenCalledWith("sess_1", 2);
    const view = makeVersionView();
    expect(calls[0].done(view, 4)).toEqual({ type: "versionSaved", seq: 4, version: view, next: { name: "saved", sessionId: "sess_1", version: 2 } });
    expect(calls[0].load).toBeNull();
  });

  it("결과가 없으면 저장하지 않는다", () => {
    const { on, calls } = setup({ session });
    on.saveVersion();
    expect(calls).toEqual([]);
  });

  it("문서 내려받기는 파일을 저장하고 알린다", () => {
    const { on, files, actions } = setup();
    const file = { filename: "AX_product_planning_V1.html", html: "<!doctype html>" };
    on.download(file);
    expect(files).toEqual([file]);
    expect(actions).toEqual([{ type: "noticed", message: DOWNLOADED_NOTICE }]);
  });
});

describe("makeHandlers — 보완·문구 수정", () => {
  it("미확인 정보를 저장하면 지금 화면에 머물며 반영을 안내한다", async () => {
    const { on, calls } = setup({ session });
    on.saveSupplements({ material: "면", size: null });
    await calls[0].request();
    expect(saveSupplements).toHaveBeenCalledWith("sess_1", { material: "면", size: null });
    const next = makeSession({ session_id: "sess_1" });
    expect(calls[0].done(next, 7)).toEqual({ type: "sessionLoaded", seq: 7, session: next, next: null, notice: SUPPLEMENTS_SAVED_NOTICE });
  });

  it("초안에 반영은 생성이고, 결과 화면에서 반영했다고 알린다", async () => {
    const { on, calls } = setup({ session });
    on.applySupplements();
    await calls[0].request();
    expect(generateResult).toHaveBeenCalledWith("sess_1");
    const result = makeResult();
    expect(calls[0].done(result, 3)).toEqual({
      type: "resultLoaded",
      seq: 3,
      result,
      next: { name: "result", sessionId: "sess_1" },
      outdatesSession: true,
      notice: SUPPLEMENTS_APPLIED_NOTICE,
    });
    expect(calls[0].outdatesSessionOnFail).toBe(true);
  });

  it("문구 수정하기는 그 섹션의 수정 화면으로, 반영하면 결과로 돌아와 알린다", async () => {
    const { on, calls, actions } = setup({ session });
    on.editSection(1);
    expect(actions).toEqual([{ type: "navigated", route: { name: "edit", sessionId: "sess_1", order: 1 } }]);
    on.submitEdit(1, "고친 문구");
    await calls[0].request();
    expect(editResultSection).toHaveBeenCalledWith("sess_1", 1, "고친 문구");
    const result = makeResult();
    expect(calls[0].done(result, 4)).toEqual({
      type: "resultLoaded",
      seq: 4,
      result,
      next: { name: "result", sessionId: "sess_1" },
      outdatesSession: false,
      notice: SECTION_EDITED_NOTICE,
    });
  });

  it("세션이 없으면 아무것도 하지 않는다", () => {
    const { on, calls, actions } = setup();
    on.saveSupplements({});
    on.applySupplements();
    on.editSection(1);
    on.submitEdit(1, "x");
    expect([calls, actions]).toEqual([[], []]);
  });
});
