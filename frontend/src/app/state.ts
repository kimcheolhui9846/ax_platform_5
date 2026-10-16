import type { ResultView, SessionView, TaskForm, TaskSummary } from "../api/types";
import { contextOf, sessionIdOf, taskOf, toHash } from "../lib/routes";
import type { Route } from "../lib/routes";

/** 기다리는 요청. seq가 다른 응답은 늦게 온 것이라 버린다. load는 화면을 그리려고 부른 요청의 이름(loadKey)이다. */
export type Inflight = { seq: number; load: string | null };

export type AppState = {
  route: Route;
  tasks: TaskSummary[];
  form: TaskForm | null; // 지금 과제의 입력 양식(요청·모드 화면)
  session: SessionView | null;
  sessionOutdated: boolean; // 결과를 만들었거나 생성이 실패해 서버 세션이 바뀌었다. 다시 받아야 한다
  result: ResultView | null;
  drafts: Record<string, string>; // 과제별 쓰다 만 요청 글
  inflight: Inflight | null;
  stalled: string | null; // 실패한 불러오기(loadKey). 같은 화면에서는 다시 부르지 않는다
  toast: string | null;
};

export type Action =
  | { type: "navigated"; route: Route }
  | { type: "requested"; seq: number; load: string | null }
  | { type: "failed"; seq: number; message: string; outdatesSession: boolean }
  | { type: "tasksLoaded"; seq: number; tasks: TaskSummary[] }
  | { type: "formLoaded"; seq: number; form: TaskForm }
  | { type: "sessionLoaded"; seq: number; session: SessionView; next: Route | null; notice: string | null }
  | { type: "resultLoaded"; seq: number; result: ResultView; next: Route | null; outdatesSession: boolean }
  | { type: "draftChanged"; task: string; text: string }
  | { type: "noticed"; message: string }
  | { type: "toastClosed" }
  | { type: "retried" };

type Settled = Exclude<Extract<Action, { seq: number }>, { type: "requested" }>;

export function initialState(route: Route): AppState {
  return {
    route,
    tasks: [],
    form: null,
    session: null,
    sessionOutdated: false,
    result: null,
    drafts: {},
    inflight: null,
    stalled: null,
    toast: null,
  };
}

export function isBusy(state: AppState): boolean {
  return state.inflight !== null;
}

/** 앱 상태는 여기서만 바뀐다(순수). 응답은 지금 기다리는 요청(inflight.seq)의 것일 때만 받는다. */
export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "navigated":
      return navigate(state, action.route);
    case "requested":
      return { ...state, inflight: { seq: action.seq, load: action.load }, toast: null };
    case "draftChanged":
      return { ...state, drafts: { ...state.drafts, [action.task]: action.text } };
    case "noticed":
      return { ...state, toast: action.message };
    case "toastClosed":
      return { ...state, toast: null };
    case "retried":
      return { ...state, stalled: null };
    default: {
      const inflight = state.inflight;
      if (inflight === null || inflight.seq !== action.seq) return state;
      return settle({ ...state, inflight: null }, inflight, action);
    }
  }
}

/** 화면 이동. 과제·세션 묶음(contextOf)을 떠나면 기다리던 요청의 응답을 버리고, 다른 과제·세션의 데이터는 비운다. */
function navigate(state: AppState, route: Route): AppState {
  if (toHash(route) === toHash(state.route)) return state;
  const sessionId = sessionIdOf(route);
  const sameSession = state.session !== null && state.session.session_id === sessionId;
  return {
    ...state,
    route,
    inflight: contextOf(route) === contextOf(state.route) ? state.inflight : null,
    stalled: null,
    form: state.form !== null && state.form.task_type === taskOf(route) ? state.form : null,
    session: sameSession ? state.session : null,
    sessionOutdated: sameSession && state.sessionOutdated,
    result: state.result !== null && state.result.session_id === sessionId ? state.result : null,
  };
}

function settle(done: AppState, inflight: Inflight, action: Settled): AppState {
  switch (action.type) {
    case "failed":
      return {
        ...done,
        toast: action.message,
        stalled: inflight.load ?? done.stalled,
        sessionOutdated: done.sessionOutdated || action.outdatesSession,
      };
    case "tasksLoaded":
      return { ...done, tasks: action.tasks };
    case "formLoaded":
      return { ...done, form: action.form };
    case "sessionLoaded":
      return {
        ...done,
        route: action.next ?? done.route,
        session: action.session,
        sessionOutdated: false,
        result: matchingResult(done.result, action.session),
        toast: action.notice ?? done.toast,
      };
    case "resultLoaded":
      return {
        ...done,
        route: action.next ?? done.route,
        result: action.result,
        sessionOutdated: done.sessionOutdated || action.outdatesSession,
      };
  }
}

/** 받은 세션에 맞는 결과만 남긴다(다른 세션이거나 결과가 없어졌으면 버린다). */
function matchingResult(result: ResultView | null, session: SessionView): ResultView | null {
  return result !== null && result.session_id === session.session_id && session.has_result ? result : null;
}
