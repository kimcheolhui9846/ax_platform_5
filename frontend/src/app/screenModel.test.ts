import { describe, expect, it } from "vitest";

import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import { makeFlowItem, makeForm, makeQuestion, makeResult, makeSession, makeTask } from "../testing/factories";
import { screenModel } from "./screenModel";
import { initialState } from "./state";
import type { AppState } from "./state";

const task = makeTask();

function at(route: Route, patch: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks: [task], ...patch };
}

describe("screenModel", () => {
  it("홈과 안내", () => {
    expect(screenModel(at(HOME))).toEqual({ kind: "home", tasks: [task] });
    expect(screenModel(at({ name: "guide" }))).toEqual({ kind: "guide" });
  });

  it("과제 목록이 없으면 홈도 불러오는 중이고, 목록을 못 받았으면 열 수 없다", () => {
    expect(screenModel(initialState(HOME))).toEqual({ kind: "loading" });
    expect(screenModel({ ...initialState(HOME), stalled: "tasks" })).toEqual({ kind: "unavailable" });
  });

  it("요청·모드는 양식과 쓰다 만 글로 그린다", () => {
    const form = makeForm();
    const state = at({ name: "mode", task: "product_planning" }, { form, drafts: { product_planning: "수제 향초" } });
    expect(screenModel(state)).toEqual({ kind: "mode", task, form, draft: "수제 향초" });
    expect(screenModel(at({ name: "request", task: "product_planning" }, { form }))).toEqual({ kind: "request", task, form, draft: "" });
  });

  it("데이터가 모자라면 불러오는 중이고, 그 불러오기가 실패했으면 열 수 없다", () => {
    const route: Route = { name: "request", task: "nope" };
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
    expect(screenModel(at(route, { session, result }))).toEqual({ kind: "result", task, session, result });
    const never = makeSession({ next_question: null, has_result: false });
    expect(screenModel(at(route, { session: never }))).toEqual({ kind: "result", task, session: never, result: null });
  });

  it("결과가 있는 세션의 결과를 아직 받지 못했으면 불러오는 중, 못 받았으면 열 수 없다", () => {
    const route: Route = { name: "result", sessionId: "sess_1" };
    const session = makeSession({ next_question: null, has_result: true });
    expect(screenModel(at(route, { session, result: makeResult({ session_id: "sess_2" }) }))).toEqual({ kind: "loading" });
    expect(screenModel(at(route, { session, stalled: "result:sess_1" }))).toEqual({ kind: "unavailable" });
  });

  it("받은 과제 목록이 비어 있어도 홈을 그린다", () => {
    expect(screenModel({ ...initialState(HOME), tasks: [] })).toEqual({ kind: "home", tasks: [] });
  });
});
