import { describe, expect, it } from "vitest";

import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import { makeForm, makeResult, makeSession, makeSessionSummary, makeTask, makeVersionView } from "../testing/factories";
import { loadKey, needsLoad } from "./load";
import { initialState } from "./state";
import type { AppState } from "./state";

const tasks = [makeTask()];

function at(route: Route, patch: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks, ...patch };
}

describe("needsLoad", () => {
  it("과제 목록이 먼저다", () => {
    expect(needsLoad(initialState(HOME))).toEqual({ kind: "tasks" });
    expect(needsLoad(at(HOME, { sessions: [] }))).toBeNull();
    // 받은 목록이 비어 있어도 다시 부르지 않는다(무한 요청 방지)
    expect(needsLoad({ ...initialState(HOME), tasks: [], sessions: [] })).toBeNull();
  });

  it("요청·모드 화면은 그 과제의 입력 양식이 있어야 한다", () => {
    const request: Route = { name: "request", task: "product_planning" };
    expect(needsLoad(at(request))).toEqual({ kind: "form", task: "product_planning" });
    expect(needsLoad(at(request, { form: makeForm() }))).toBeNull();
    expect(needsLoad(at({ name: "mode", task: "branding" }, { form: makeForm() }))).toEqual({ kind: "form", task: "branding" });
  });

  it("세션 화면은 그 세션이 있어야 하고, 낡았으면 다시 받는다", () => {
    const question: Route = { name: "question", sessionId: "sess_1" };
    expect(needsLoad(at(question))).toEqual({ kind: "session", sessionId: "sess_1" });
    expect(needsLoad(at(question, { session: makeSession() }))).toBeNull();
    expect(needsLoad(at(question, { session: makeSession({ session_id: "sess_2" }) }))).toEqual({ kind: "session", sessionId: "sess_1" });
    expect(needsLoad(at(question, { session: makeSession(), sessionOutdated: true }))).toEqual({ kind: "session", sessionId: "sess_1" });
  });

  it("결과 화면은 결과가 있는 세션이면 결과까지 받는다", () => {
    const result: Route = { name: "result", sessionId: "sess_1" };
    const done = makeSession({ next_question: null, has_result: true });
    expect(needsLoad(at(result, { session: done }))).toEqual({ kind: "result", sessionId: "sess_1" });
    expect(needsLoad(at(result, { session: done, result: makeResult() }))).toBeNull();
    expect(needsLoad(at(result, { session: makeSession({ has_result: false }) }))).toBeNull();
  });

  it("기다리는 요청이 있거나 같은 불러오기가 실패했으면 부르지 않는다", () => {
    const question: Route = { name: "question", sessionId: "sess_1" };
    expect(needsLoad(at(question, { inflight: { seq: 1, load: null } }))).toBeNull();
    expect(needsLoad(at(question, { stalled: "session:sess_1" }))).toBeNull();
    expect(needsLoad(at(question, { stalled: "form:branding" }))).toEqual({ kind: "session", sessionId: "sess_1" });
  });
});

describe("loadKey", () => {
  it("불러오기마다 다른 이름이다", () => {
    expect(loadKey({ kind: "tasks" })).toBe("tasks");
    expect(loadKey({ kind: "form", task: "branding" })).toBe("form:branding");
    expect(loadKey({ kind: "session", sessionId: "s" })).toBe("session:s");
    expect(loadKey({ kind: "result", sessionId: "s" })).toBe("result:s");
  });
});

describe("needsLoad — 묶음 2 화면", () => {
  it("홈·내 작업·결과물은 내 세션 목록이 있어야 한다", () => {
    for (const route of [HOME, { name: "work" }, { name: "documents" }] as Route[]) {
      expect(needsLoad(at(route))).toEqual({ kind: "sessions" });
      expect(needsLoad(at(route, { sessions: [makeSessionSummary()] }))).toBeNull();
    }
  });

  it("저장 완료 화면은 저장한 그 버전이 있어야 한다", () => {
    const saved: Route = { name: "saved", sessionId: "sess_1", version: 1 };
    const done = makeSession({ next_question: null, has_result: true });
    expect(needsLoad(at(saved, { session: done }))).toEqual({ kind: "version", sessionId: "sess_1", version: 1 });
    expect(needsLoad(at(saved, { session: done, version: makeVersionView() }))).toBeNull();
  });

  it("버전 보기는 세션 다음에 그 버전", () => {
    const route: Route = { name: "version", sessionId: "sess_1", version: 2 };
    expect(needsLoad(at(route))).toEqual({ kind: "session", sessionId: "sess_1" });
    const session = makeSession({ next_question: null, has_result: true });
    expect(needsLoad(at(route, { session }))).toEqual({ kind: "version", sessionId: "sess_1", version: 2 });
    const two = makeVersionView({ version: { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate", saved: false } });
    expect(needsLoad(at(route, { session, version: two }))).toBeNull();
    expect(needsLoad(at(route, { session, version: makeVersionView() }))).toEqual({ kind: "version", sessionId: "sess_1", version: 2 });
  });

  it("목록·버전 불러오기의 이름", () => {
    expect(loadKey({ kind: "sessions" })).toBe("sessions");
    expect(loadKey({ kind: "version", sessionId: "s", version: 3 })).toBe("version:s:3");
  });
});
