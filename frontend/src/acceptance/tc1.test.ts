import { describe, expect, it } from "vitest";

import type { EvidenceItem } from "../api/types";
import { needsLoad } from "../app/load";
import type { Load } from "../app/load";
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
const LAST = makeQuestion({ question_id: "q_9", field: "field_9" });
const ANSWERING = makeSession({
  mode: "precise",
  next_question: LAST,
  summary: SUMMARY.slice(0, 9),
  flow: [...ANSWERED.slice(0, 9), makeFlowItem({ field: "field_9", status: "current", question: LAST })],
});
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
const EVIDENCE_ITEMS: EvidenceItem[] = Array.from({ length: 5 }, (_, i) => ({
  id: `source_${i}`,
  title: `근거 자료 ${i + 1}`,
  publisher: "발행 기관",
  meta: "2026 · 보고서",
  summary: "자료 요약 문장. ".repeat(40),
  scope: "적용 범위",
  url: "https://example.com/report",
  applies_to: "diagnosis",
  record: null,
}));
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

/** route 화면에 과제 목록을 받아 둔 상태. */
function at(route: Route, data: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks: TASKS, ...data };
}

type Transition = { name: string; from: AppState; actions: Action[]; screen: string };
type Arrival = { screen: string; load: Load | null };

/** 도착한 화면. 질문 화면은 어느 질문인지, 결과 화면은 결과가 있는지까지 본다. */
function shown(model: ScreenModel): string {
  if (model.kind === "question") return `question:${model.question.question_id}`;
  if (model.kind === "result") return `result:${model.result === null ? "empty" : "ready"}`;
  return model.kind;
}

/** 화면 전환 하나: 동작을 reducer에 넣고, 그릴 화면과 불러올 데이터를 정한다. */
function transit(t: Transition): Arrival {
  const state = t.actions.reduce(reducer, t.from);
  return { screen: shown(screenModel(state)), load: needsLoad(state) };
}

/** 화면 전환마다 도착한 화면이 맞고 더 불러올 데이터가 없는지, 계산 시간 중앙값이 기준 이하인지 확인한다. */
function check(transitions: Transition[]) {
  for (const t of transitions) {
    expect(transit(t), t.name).toEqual({ screen: t.screen, load: null });
    expect(medianMs(() => transit(t)), t.name).toBeLessThanOrEqual(LIMIT_MS);
  }
}

/** 버튼이나 불러오기가 보낸 요청(seq). 응답 동작은 같은 seq일 때만 받아들여진다. */
function requested(seq: number, load: string | null, generating = false): Action {
  return { type: "requested", seq, load, generating };
}

// 시작 상태는 실제 앱이 그 화면에서 가질 수 있는 상태다(이동하면 다른 과제·세션의 데이터는 비워진다).
// 응답을 기다리는 전환은 요청부터 응답, 이어지는 불러오기까지 넣어 도착 화면에 모자란 데이터가 없게 한다.
const QUESTION_FLOW: Transition[] = [
  {
    name: "홈 → 요청(과제 카드, 입력 양식 응답)",
    from: at(HOME, { sessions: SESSIONS }),
    actions: [{ type: "navigated", route: REQUEST }, requested(1, "form:product_planning"), { type: "formLoaded", seq: 1, form: FORM }],
    screen: "request",
  },
  { name: "요청 → 모드(다음)", from: at(REQUEST, { form: FORM }), actions: [{ type: "navigated", route: MODE }], screen: "mode" },
  {
    name: "모드 → 첫 질문(모드 선택, 세션 만들기 응답)",
    from: at(MODE, { form: FORM }),
    actions: [requested(1, null), { type: "sessionLoaded", seq: 1, session: ASKING, next: QUESTION, noticeConsumed: "product_planning", notice: null }],
    screen: "question:q_next",
  },
  {
    name: "질문 → 다음 질문(답하기 응답)",
    from: at(QUESTION, { session: ANSWERING }),
    actions: [requested(1, null), { type: "sessionLoaded", seq: 1, session: ASKING, next: QUESTION, noticeConsumed: null, notice: null }],
    screen: "question:q_next",
  },
  {
    // ASKING에 걸린 q_next가 마지막 질문이다. 답하면 남은 질문이 없는 세션(CONFIRMING)이 온다
    name: "마지막 질문 → 확인(답하기 응답)",
    from: at(QUESTION, { session: ASKING }),
    actions: [requested(1, null), { type: "sessionLoaded", seq: 1, session: CONFIRMING, next: CONFIRM, noticeConsumed: null, notice: null }],
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
    actions: [requested(1, null, true)],
    screen: "generating",
  },
  {
    // 생성 응답은 세션을 낡게 표시하므로 세션을 다시 받아야 결과가 보인다
    name: "생성 중 → 결과(생성 응답, 세션 다시 받기)",
    from: at(CONFIRM, { session: CONFIRMING }),
    actions: [
      requested(1, null, true),
      { type: "resultLoaded", seq: 1, result: RESULT, next: RESULT_ROUTE, outdatesSession: true, notice: null },
      requested(2, `session:${SID}`),
      { type: "sessionLoaded", seq: 2, session: DONE, next: null, noticeConsumed: null, notice: null },
    ],
    screen: "result:ready",
  },
  {
    name: "결과 → 문구 수정",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT }),
    actions: [{ type: "navigated", route: { name: "edit", sessionId: SID, order: 3 } }],
    screen: "edit",
  },
  {
    name: "결과 → 근거 검토(이동, 자료 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT }),
    actions: [{ type: "navigated", route: EVIDENCE }, requested(1, `evidence:${SID}`), { type: "evidenceLoaded", seq: 1, sessionId: SID, items: EVIDENCE_ITEMS }],
    screen: "evidence",
  },
  {
    name: "결과 → 저장 완료(저장 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT }),
    actions: [requested(1, null), { type: "versionSaved", seq: 1, version: SAVED_VERSION, next: SAVED }],
    screen: "saved",
  },
  {
    name: "내 작업 → 버전 보기(이동, 세션·버전 응답)",
    from: at(WORK, { sessions: SESSIONS }),
    actions: [
      { type: "navigated", route: VERSION },
      requested(1, `session:${SID}`),
      { type: "sessionLoaded", seq: 1, session: DONE, next: null, noticeConsumed: null, notice: null },
      requested(2, `version:${SID}:1`),
      { type: "versionLoaded", seq: 2, version: SAVED_VERSION },
    ],
    screen: "version",
  },
];

const LIST_FLOW: Transition[] = [
  {
    name: "결과 → 내 작업(메뉴, 목록 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT, sessions: SESSIONS }),
    actions: [
      { type: "navigated", route: WORK },
      requested(1, "sessions"),
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
