import { describe, expect, it } from "vitest";

import { needsLoad } from "../app/load";
import { screenModel } from "../app/screenModel";
import type { ScreenModel } from "../app/screenModel";
import { initialState, reducer } from "../app/state";
import type { Action, AppState } from "../app/state";
import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import {
  makeFlowItem,
  makeForm,
  makeQuestion,
  makeResult,
  makeSession,
  makeSessionSummary,
  makeTask,
  makeVersionView,
} from "../testing/factories";
import { medianMs } from "../testing/timing";

// TC1: 버튼을 눌러 다음 화면으로 넘어갈 때, 네트워크를 뺀 계산(상태 갱신 reducer → 화면 판단 screenModel·needsLoad)이
// 화면 전환마다 중앙값 0.5ms 이하인지 잰다. 데이터는 실제보다 크게 잡는다(작업 200개, 정밀 모드 답 10개, 섹션 12개).
const LIMIT_MS = 0.5;

const TASKS = ["business_plan", "product_planning", "branding", "marketing", "ir_pitch"].map((task_type) => makeTask({ task_type }));
const SESSIONS = Array.from({ length: 200 }, (_, i) => makeSessionSummary({ session_id: `sess_${i}` }));
const FORM = makeForm();

const FIELDS = Array.from({ length: 10 }, (_, i) => `field_${i}`);
const ROW = makeSession().summary[0];
const SUMMARY = FIELDS.map((field) => ({ ...ROW, field }));
const ANSWERED = FIELDS.map((field, i) =>
  makeFlowItem({ field, status: "answered", answer: "답", question: makeQuestion({ question_id: `q_${i}`, field }) }),
);
const NEXT = makeQuestion({ question_id: "q_next", field: "extra" });
const ASKING = makeSession({
  mode: "precise",
  next_question: NEXT,
  summary: SUMMARY,
  flow: [...ANSWERED, makeFlowItem({ field: "extra", status: "current", question: NEXT })],
});
const CONFIRMING = makeSession({ mode: "precise", next_question: null, summary: SUMMARY, flow: ANSWERED });
const DONE = { ...CONFIRMING, has_result: true };

const BASE_RESULT = makeResult();
const SECTIONS = Array.from({ length: 12 }, (_, i) => ({
  ...BASE_RESULT.result.sections[0],
  order: i + 1,
  heading: `섹션 ${i + 1}`,
  blocks: [{ type: "text" as const, text: "본문 문장. ".repeat(200) }],
}));
const RESULT = makeResult({ summary: SUMMARY, result: { ...BASE_RESULT.result, sections: SECTIONS } });
const SAVED_VERSION = makeVersionView({
  version: { ...RESULT.version, saved: true },
  result: RESULT.result,
  summary: SUMMARY,
});

const SID = ASKING.session_id;
const REQUEST: Route = { name: "request", task: "product_planning", from: null };
const MODE: Route = { name: "mode", task: "product_planning", from: null };
const QUESTION: Route = { name: "question", sessionId: SID };
const CONFIRM: Route = { name: "confirm", sessionId: SID };
const RESULT_ROUTE: Route = { name: "result", sessionId: SID };
const EVIDENCE: Route = { name: "evidence", sessionId: SID };
const SAVED: Route = { name: "saved", sessionId: SID, version: 1 };
const VERSION: Route = { name: "version", sessionId: SID, version: 1 };
const WORK: Route = { name: "work" };
const DOCUMENTS: Route = { name: "documents" };

/** 응답을 기다리는 요청(seq 1). 응답 동작은 이 요청의 것일 때만 받아들여진다. */
const WAITING = { seq: 1, load: null, generating: false };

/** route 화면에 과제 목록을 받아 둔 상태. */
function at(route: Route, data: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks: TASKS, ...data };
}

type Transition = { name: string; from: AppState; actions: Action[]; screen: ScreenModel["kind"] };

/** 화면 전환 하나: 동작을 reducer에 넣고, 그릴 화면과 불러올 데이터를 정한다. */
function transit(t: Transition): ScreenModel["kind"] {
  const state = t.actions.reduce(reducer, t.from);
  needsLoad(state);
  return screenModel(state).kind;
}

/** 화면 전환마다 도착한 화면이 맞는지, 계산 시간 중앙값이 기준 이하인지 확인한다. */
function check(transitions: Transition[]) {
  for (const t of transitions) {
    expect(transit(t), t.name).toBe(t.screen);
    expect(medianMs(() => transit(t)), t.name).toBeLessThanOrEqual(LIMIT_MS);
  }
}

const QUESTION_FLOW: Transition[] = [
  { name: "홈 → 요청(과제 카드)", from: at(HOME, { sessions: SESSIONS, form: FORM }), actions: [{ type: "navigated", route: REQUEST }], screen: "request" },
  { name: "요청 → 모드(다음)", from: at(REQUEST, { form: FORM }), actions: [{ type: "navigated", route: MODE }], screen: "mode" },
  {
    name: "모드 → 첫 질문(세션 만들기 응답)",
    from: at(MODE, { form: FORM, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: ASKING, next: QUESTION, noticeConsumed: "product_planning", notice: null }],
    screen: "question",
  },
  {
    name: "질문 → 다음 질문(답하기 응답)",
    from: at(QUESTION, { session: ASKING, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: ASKING, next: null, noticeConsumed: null, notice: null }],
    screen: "question",
  },
  {
    name: "마지막 질문 → 확인(답하기 응답)",
    from: at(QUESTION, { session: ASKING, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: CONFIRMING, next: CONFIRM, noticeConsumed: null, notice: null }],
    screen: "confirm",
  },
  {
    name: "질문 → 답 고치기(흐름 패널)",
    from: at(QUESTION, { session: ASKING }),
    actions: [{ type: "navigated", route: { name: "revise", sessionId: SID, questionId: "q_0" } }],
    screen: "revise",
  },
];

const RESULT_FLOW: Transition[] = [
  {
    name: "확인 → 생성 중(초안 만들기)",
    from: at(CONFIRM, { session: CONFIRMING }),
    actions: [{ type: "requested", seq: 1, load: null, generating: true }],
    screen: "generating",
  },
  {
    name: "생성 중 → 결과(생성 응답)",
    from: at(CONFIRM, { session: CONFIRMING, inflight: { seq: 1, load: null, generating: true } }),
    actions: [{ type: "resultLoaded", seq: 1, result: RESULT, next: RESULT_ROUTE, outdatesSession: true, notice: null }],
    screen: "result",
  },
  {
    name: "결과 → 문구 수정",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT }),
    actions: [{ type: "navigated", route: { name: "edit", sessionId: SID, order: 3 } }],
    screen: "edit",
  },
  {
    name: "결과 → 근거 검토(자료 응답)",
    from: at(EVIDENCE, { session: DONE, result: RESULT, inflight: WAITING }),
    actions: [{ type: "evidenceLoaded", seq: 1, sessionId: SID, items: [] }],
    screen: "evidence",
  },
  {
    name: "결과 → 저장 완료(저장 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT, inflight: WAITING }),
    actions: [{ type: "versionSaved", seq: 1, version: SAVED_VERSION, next: SAVED }],
    screen: "saved",
  },
  {
    name: "내 작업 → 버전 보기(버전 응답)",
    from: at(VERSION, { session: DONE, inflight: WAITING }),
    actions: [{ type: "versionLoaded", seq: 1, version: SAVED_VERSION }],
    screen: "version",
  },
];

const LIST_FLOW: Transition[] = [
  {
    name: "결과 → 내 작업(메뉴, 목록 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT, sessions: SESSIONS }),
    actions: [
      { type: "navigated", route: WORK },
      { type: "requested", seq: 1, load: "sessions", generating: false },
      { type: "sessionsLoaded", seq: 1, sessions: SESSIONS },
    ],
    screen: "work",
  },
  { name: "내 작업 → 결과물(메뉴)", from: at(WORK, { sessions: SESSIONS }), actions: [{ type: "navigated", route: DOCUMENTS }], screen: "documents" },
  { name: "결과물 → 홈(메뉴)", from: at(DOCUMENTS, { sessions: SESSIONS }), actions: [{ type: "navigated", route: HOME }], screen: "home" },
];

describe("TC1 화면 전환 계산 시간", () => {
  it("TC1-1 질문 흐름의 화면 전환(홈→요청→모드→질문→확인·답 고치기)은 0.5ms 이하", () => {
    check(QUESTION_FLOW);
  });

  it("TC1-2 결과 흐름의 화면 전환(생성 중→결과→문구 수정·근거·저장·버전)은 0.5ms 이하", () => {
    check(RESULT_FLOW);
  });

  it("TC1-3 목록 화면 전환(작업 200개, 내 작업·결과물·홈)은 0.5ms 이하", () => {
    check(LIST_FLOW);
  });
});
