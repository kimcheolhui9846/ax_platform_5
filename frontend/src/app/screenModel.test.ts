import { describe, expect, it } from "vitest";

import type { EvidenceItem } from "../api/types";
import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import { makeContext, makeFlowItem, makeForm, makeQuestion, makeResult, makeSession, makeSessionSummary, makeTask, makeVersionView } from "../testing/factories";
import { screenModel } from "./screenModel";
import { initialState } from "./state";
import type { AppState } from "./state";

const task = makeTask();

function at(route: Route, patch: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks: [task], ...patch };
}

describe("screenModel", () => {
  it("홈과 안내", () => {
    expect(screenModel(at(HOME, { sessions: [] }))).toEqual({ kind: "home", tasks: [task], sessions: [] });
    expect(screenModel(at({ name: "guide" }))).toEqual({ kind: "guide" });
  });

  it("과제 목록이 없으면 홈도 불러오는 중이고, 목록을 못 받았으면 열 수 없다", () => {
    expect(screenModel(initialState(HOME))).toEqual({ kind: "loading" });
    expect(screenModel({ ...initialState(HOME), stalled: "tasks" })).toEqual({ kind: "unavailable" });
  });

  it("요청·모드는 양식과 쓰다 만 글로 그린다", () => {
    const form = makeForm();
    const state = at({ name: "mode", task: "product_planning", from: null }, { form, drafts: { product_planning: "수제 향초" } });
    expect(screenModel(state)).toEqual({ kind: "mode", task, form, draft: "수제 향초", context: null });
    expect(screenModel(at({ name: "request", task: "product_planning", from: null }, { form }))).toEqual({ kind: "request", task, form, draft: "", context: null });
  });

  it("데이터가 모자라면 불러오는 중이고, 그 불러오기가 실패했으면 열 수 없다", () => {
    const route: Route = { name: "request", task: "nope", from: null };
    expect(screenModel(at(route))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { stalled: "form:nope" }))).toEqual({ kind: "unavailable" });
    expect(screenModel(at({ name: "question", sessionId: "sess_1" }))).toEqual({ kind: "loading" });
  });

  it("질문 주소는 걸린 질문이 있으면 질문, 없으면 답변 확인이다", () => {
    const route: Route = { name: "question", sessionId: "sess_1" };
    const session = makeSession();
    expect(screenModel(at(route, { session }))).toEqual({ kind: "question", task, session, question: session.next_question });
    const done = makeSession({ next_question: null });
    expect(screenModel(at(route, { session: done }))).toEqual({ kind: "confirm", task, session: done });
  });

  it("답변 확인 주소는 질문이 걸려 있어도 확인이다(현재 정보로 초안 만들기)", () => {
    const session = makeSession();
    expect(screenModel(at({ name: "confirm", sessionId: "sess_1" }, { session }))).toEqual({ kind: "confirm", task, session });
  });

  it("고치기 주소는 답했거나 미정인 항목이면 그 항목, 아니면 질문 화면이다", () => {
    const answered = makeFlowItem({ status: "answered", answer: "부모", question: makeQuestion({ question_id: "q_0" }) });
    const session = makeSession({ flow: [answered, makeFlowItem({ status: "current", question: makeQuestion() })] });
    expect(screenModel(at({ name: "revise", sessionId: "sess_1", questionId: "q_0" }, { session }))).toEqual({
      kind: "revise",
      task,
      session,
      item: answered,
    });
    expect(screenModel(at({ name: "revise", sessionId: "sess_1", questionId: "q_1" }, { session })).kind).toBe("question");
    expect(screenModel(at({ name: "revise", sessionId: "sess_1", questionId: "q_없음" }, { session })).kind).toBe("question");
  });

  it("결과 주소는 그 세션의 결과로 그리고, 아직 만들지 않았으면 null이다", () => {
    const route: Route = { name: "result", sessionId: "sess_1" };
    const session = makeSession({ next_question: null, has_result: true });
    const result = makeResult();
    expect(screenModel(at(route, { session, result }))).toEqual({ kind: "result", task, session, result, images: {} });
    const never = makeSession({ next_question: null, has_result: false });
    expect(screenModel(at(route, { session: never }))).toEqual({ kind: "result", task, session: never, result: null, images: {} });
  });

  it("결과가 있는 세션의 결과를 아직 받지 못했으면 불러오는 중, 못 받았으면 열 수 없다", () => {
    const route: Route = { name: "result", sessionId: "sess_1" };
    const session = makeSession({ next_question: null, has_result: true });
    expect(screenModel(at(route, { session, result: makeResult({ session_id: "sess_2" }) }))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { session, stalled: "result:sess_1" }))).toEqual({ kind: "unavailable" });
  });

  it("받은 과제 목록이 비어 있어도 홈을 그린다", () => {
    expect(screenModel({ ...initialState(HOME), tasks: [], sessions: [] })).toEqual({ kind: "home", tasks: [], sessions: [] });
  });

  it("홈은 내 세션 목록을 받기 전에는 불러오는 중이다", () => {
    expect(screenModel(at(HOME))).toEqual({ kind: "loading" });
  });

  it("내 작업·결과물은 내 세션 목록으로 그린다", () => {
    const sessions = [makeSessionSummary()];
    expect(screenModel(at({ name: "work" }, { sessions }))).toEqual({ kind: "work", sessions });
    expect(screenModel(at({ name: "documents" }, { sessions }))).toEqual({ kind: "documents", sessions });
    expect(screenModel(at({ name: "work" }))).toEqual({ kind: "loading" });
  });

  it("저장 완료는 저장한 그 버전으로 그린다(지금 결과가 아니다)", () => {
    const route: Route = { name: "saved", sessionId: "sess_1", version: 1 };
    const session = makeSession({ next_question: null, has_result: true });
    const version = makeVersionView({ version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true } });
    expect(screenModel(at(route, { session, version, result: makeResult() }))).toEqual({ kind: "saved", task, session, version, images: {} });
    expect(screenModel(at(route, { session }))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { session, stalled: "version:sess_1:1" }))).toEqual({ kind: "unavailable" });
  });

  it("저장하지 않은 버전 번호로 저장 완료 주소를 열면 버전 보기로 보여 준다", () => {
    const route: Route = { name: "saved", sessionId: "sess_1", version: 1 };
    const session = makeSession({ next_question: null, has_result: true });
    const unsaved = makeVersionView();
    expect(screenModel(at(route, { session, version: unsaved }))).toEqual({ kind: "version", task, session, version: unsaved, images: {} });
  });

  it("내 세션 목록을 못 받아도 홈은 이어하기 없이 열린다(새 과제는 시작할 수 있다)", () => {
    expect(screenModel(at(HOME, { stalled: "sessions" }))).toEqual({ kind: "home", tasks: [task], sessions: [] });
  });

  it("버전 보기는 그 버전을 받아야 그린다", () => {
    const route: Route = { name: "version", sessionId: "sess_1", version: 1 };
    const session = makeSession({ next_question: null, has_result: true });
    const version = makeVersionView();
    expect(screenModel(at(route, { session, version }))).toEqual({ kind: "version", task, session, version, images: {} });
    expect(screenModel(at(route, { session }))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { session, stalled: "version:sess_1:1" }))).toEqual({ kind: "unavailable" });
  });

  it("문구 수정 주소는 그 섹션이 있으면 수정 화면, 없으면 결과 화면이다", () => {
    const route: Route = { name: "edit", sessionId: "sess_1", order: 1 };
    const session = makeSession({ session_id: "sess_1", has_result: true });
    const result = makeResult({ session_id: "sess_1" });
    const base = { ...initialState(route), tasks: [makeTask()], session };
    expect(screenModel(base).kind).toBe("loading");
    const model = screenModel({ ...base, result });
    expect(model).toEqual({ kind: "edit", task: makeTask(), session, result, section: result.result.sections[0], images: {} });
    const missing = screenModel({ ...base, route: { ...route, order: 99 }, result });
    expect(missing).toEqual({ kind: "result", task: makeTask(), session, result, images: {} });
    const noResult = makeSession({ session_id: "sess_1", has_result: false });
    expect(screenModel({ ...base, session: noResult })).toEqual({ kind: "result", task: makeTask(), session: noResult, result: null, images: {} });
  });

  it("결과·수정·저장 완료·버전 보기 모델에는 받아 둔 이미지가 실린다", () => {
    const assets = { a: "data:image/svg+xml;base64,AA", b: null };
    const session = makeSession({ session_id: "sess_1", next_question: null, has_result: true });
    const result = makeResult({ session_id: "sess_1" });
    const shown = screenModel(at({ name: "result", sessionId: "sess_1" }, { session, result, assets }));
    expect(shown).toMatchObject({ kind: "result", images: assets });
  });

  it("근거 검토 주소는 세션·결과·자료가 모두 있어야 그린다", () => {
    const route: Route = { name: "evidence", sessionId: "sess_1" };
    const session = makeSession({ session_id: "sess_1", next_question: null, has_result: true });
    const result = makeResult({ session_id: "sess_1" });
    const items: EvidenceItem[] = [];
    expect(screenModel(at(route, { session, result }))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { session, result, evidence: { sessionId: "sess_1", items } }))).toEqual({
      kind: "evidence",
      task,
      session,
      result,
      items,
    });
    const noResult = makeSession({ session_id: "sess_1", next_question: null, has_result: false });
    expect(screenModel(at(route, { session: noResult }))).toEqual({ kind: "result", task, session: noResult, result: null, images: {} });
  });
});

describe("이미지를 받아 둔 상태", () => {
  const assets = { a: "data:image/svg+xml;base64,AA", b: null };

  it("수정·저장 완료·버전 보기 모델에도 받아 둔 이미지가 실린다", () => {
    const session = makeSession({ session_id: "sess_1", next_question: null, has_result: true });
    const result = makeResult({ session_id: "sess_1" });
    expect(screenModel(at({ name: "edit", sessionId: "sess_1", order: 1 }, { session, result, assets }))).toMatchObject({ kind: "edit", images: assets });
    const saved = makeVersionView({ version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true } });
    expect(screenModel(at({ name: "saved", sessionId: "sess_1", version: 1 }, { session, version: saved, assets }))).toMatchObject({ kind: "saved", images: assets });
    expect(screenModel(at({ name: "version", sessionId: "sess_1", version: 1 }, { session, version: makeVersionView(), assets }))).toMatchObject({
      kind: "version",
      images: assets,
    });
  });

  it("실패 주소는 세션이 있으면 세션 상태와 상관없이 실패 화면이다, 생성 중이면 생성 중이 먼저다", () => {
    const route: Route = { name: "failed", sessionId: "sess_1" };
    for (const session of [makeSession(), makeSession({ next_question: null })]) {
      expect(screenModel(at(route, { session }))).toEqual({ kind: "failed", task, session });
    }
    const session = makeSession();
    expect(screenModel(at(route, { session, inflight: { seq: 1, load: null, generating: true } }))).toEqual({ kind: "generating", task, session });
    expect(screenModel(at(route, {}))).toEqual({ kind: "loading" });
  });

  it("초안을 만드는 동안은 세션 화면이 생성 중 화면이다", () => {
    const session = makeSession();
    const inflight = { seq: 1, load: null, generating: true };
    const edit: Route = { name: "edit", sessionId: "sess_1", order: 1 };
    for (const route of [{ name: "confirm", sessionId: "sess_1" } as Route, { name: "result", sessionId: "sess_1" } as Route, edit]) {
      expect(screenModel(at(route, { session, inflight }))).toEqual({ kind: "generating", task, session });
    }
    expect(screenModel(at({ name: "confirm", sessionId: "sess_1" }, { inflight }))).toEqual({ kind: "loading" });
    expect(screenModel(at(HOME, { sessions: [], session, inflight }))).toEqual({ kind: "home", tasks: [task], sessions: [] });
    expect(screenModel(at({ name: "confirm", sessionId: "sess_1" }, { session, inflight: { ...inflight, generating: false } }))).toMatchObject({ kind: "confirm" });
  });
});

describe("screenModel — 이어가기", () => {
  const from = { sessionId: "s1", version: 2 };
  const form = makeForm();
  const context = makeContext();

  it("출처가 있으면 미리보기가 올 때까지 loading, 맞으면 context를 싣는다", () => {
    const route: Route = { name: "request", task: "product_planning", from };
    expect(screenModel(at(route, { form }))).toEqual({ kind: "loading" });
    const carry = { key: "product_planning:s1:2", context };
    expect(screenModel(at(route, { form, carry }))).toEqual({ kind: "request", task, form, draft: "", context });
    expect(screenModel(at(route, { form, carry: { key: "product_planning:other:1", context } }))).toEqual({ kind: "loading" });
  });

  it("출처가 없으면 context는 null", () => {
    const model = screenModel(at({ name: "mode", task: "product_planning", from: null }, { form, carry: { key: "x", context } }));
    expect(model).toMatchObject({ kind: "mode", context: null });
  });
});
