import type { EvidenceItem, ResultView, SessionSummary, SessionView, TaskForm, TaskSummary, VersionView } from "../api/types";
import type { Images } from "../lib/document";
import { contextOf, isListRoute, sessionIdOf, taskOf, toHash } from "../lib/routes";
import type { Route } from "../lib/routes";

/** 기다리는 요청. seq가 다른 응답은 늦게 온 것이라 버린다. load는 화면을 그리려고 부른 요청의 이름(loadKey)이다. */
export type Inflight = { seq: number; load: string | null; generating: boolean };

export type AppState = {
  route: Route;
  tasks: TaskSummary[] | null; // 아직 받지 않았으면 null
  sessions: SessionSummary[] | null; // 내 세션 목록. 목록 화면(홈·내 작업·결과물)에 새로 들어올 때마다 다시 받는다
  form: TaskForm | null; // 지금 과제의 입력 양식(요청·모드 화면)
  session: SessionView | null;
  sessionOutdated: boolean; // 결과를 만들었거나 생성이 실패해 서버 세션이 바뀌었다. 다시 받아야 한다
  result: ResultView | null;
  version: VersionView | null; // 버전 보기·저장 완료 화면의 버전
  evidence: { sessionId: string; items: EvidenceItem[] } | null; // 근거 검토 화면의 자료
  assets: Images; // 결과 이미지(asset_id → data URL). 화면 불러오기와 따로 받는다
  drafts: Record<string, string>; // 과제별 쓰다 만 요청 글
  inflight: Inflight | null;
  stalled: string | null; // 실패한 불러오기(loadKey). 같은 화면에서는 다시 부르지 않는다
  toast: string | null;
};

export type Action =
  | { type: "navigated"; route: Route }
  | { type: "requested"; seq: number; load: string | null; generating: boolean }
  | { type: "failed"; seq: number; message: string; outdatesSession: boolean; next: Route | null }
  | { type: "tasksLoaded"; seq: number; tasks: TaskSummary[] }
  | { type: "sessionsLoaded"; seq: number; sessions: SessionSummary[] }
  | { type: "formLoaded"; seq: number; form: TaskForm }
  | { type: "sessionLoaded"; seq: number; session: SessionView; next: Route | null; notice: string | null }
  | { type: "resultLoaded"; seq: number; result: ResultView; next: Route | null; outdatesSession: boolean; notice: string | null }
  | { type: "versionLoaded"; seq: number; version: VersionView }
  | { type: "versionSaved"; seq: number; version: VersionView; next: Route | null }
  | { type: "evidenceLoaded"; seq: number; sessionId: string; items: EvidenceItem[] }
  | { type: "assetRequested"; assetId: string }
  | { type: "assetLoaded"; assetId: string; url: string | null }
  | { type: "draftChanged"; task: string; text: string }
  | { type: "noticed"; message: string }
  | { type: "toastClosed" }
  | { type: "retried" };

type Settled = Exclude<Extract<Action, { seq: number }>, { type: "requested" }>;

export function initialState(route: Route): AppState {
  return {
    route,
    tasks: null,
    sessions: null,
    form: null,
    session: null,
    sessionOutdated: false,
    result: null,
    version: null,
    evidence: null,
    assets: {},
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
      // 버튼 요청은 이전 알림을 지운다. 불러오기는 지우지 않는다(생성 실패 알림 뒤 곧바로 세션을 다시 받는다)
      return { ...state, inflight: { seq: action.seq, load: action.load, generating: action.generating }, toast: action.load === null ? null : state.toast };
    case "draftChanged":
      return { ...state, drafts: { ...state.drafts, [action.task]: action.text } };
    case "noticed":
      return { ...state, toast: action.message };
    case "assetRequested":
      return { ...state, assets: { ...state.assets, [action.assetId]: null } };
    case "assetLoaded":
      // 이미지는 id로 가려서 늦게 와도 맞는 자리에 들어간다. 다른 세션으로 떠난 뒤 온 것은 버린다
      return action.assetId in state.assets ? { ...state, assets: { ...state.assets, [action.assetId]: action.url } } : state;
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

/**
 * 화면 이동. 과제·세션 묶음(contextOf)을 떠나면 기다리던 요청의 응답을 버리고, 다른 과제·세션의 데이터는 비운다.
 * 목록 화면에 새로 들어오면 내 세션 목록을 다시 받는다(그사이 답하거나 저장했을 수 있다).
 */
function navigate(state: AppState, route: Route): AppState {
  if (toHash(route) === toHash(state.route)) return state;
  const sessionId = sessionIdOf(route);
  const sameSession = state.session !== null && state.session.session_id === sessionId;
  return {
    ...state,
    route,
    inflight: contextOf(route) === contextOf(state.route) ? state.inflight : null,
    stalled: null,
    sessions: isListRoute(route) && !isListRoute(state.route) ? null : state.sessions,
    form: state.form !== null && state.form.task_type === taskOf(route) ? state.form : null,
    session: sameSession ? state.session : null,
    sessionOutdated: sameSession && state.sessionOutdated,
    result: state.result !== null && state.result.session_id === sessionId ? state.result : null,
    version: sameVersion(state.version, route) ? state.version : null,
    evidence: state.evidence !== null && state.evidence.sessionId === sessionId ? state.evidence : null,
    assets: sameSession ? state.assets : {},
  };
}

/** 이동한 주소가 지금 들고 있는 버전을 보는 주소인지. */
function sameVersion(version: VersionView | null, route: Route): boolean {
  return (
    version !== null &&
    (route.name === "version" || route.name === "saved") &&
    version.session_id === route.sessionId &&
    version.version.version === route.version
  );
}

function settle(done: AppState, inflight: Inflight, action: Settled): AppState {
  switch (action.type) {
    case "failed":
      return {
        ...done,
        route: action.next ?? done.route,
        toast: action.message,
        stalled: inflight.load ?? done.stalled,
        sessionOutdated: done.sessionOutdated || action.outdatesSession,
      };
    case "tasksLoaded":
      return { ...done, tasks: action.tasks };
    case "sessionsLoaded":
      return { ...done, sessions: action.sessions };
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
        toast: action.notice ?? done.toast,
      };
    case "evidenceLoaded":
      return { ...done, evidence: { sessionId: action.sessionId, items: action.items } };
    case "versionLoaded":
      return { ...done, version: action.version };
    case "versionSaved":
      // 지금 결과의 저장 표시가 바뀌었으므로 결과는 다시 받는다
      return { ...done, route: action.next ?? done.route, version: action.version, result: null };
  }
}

/** 받은 세션에 맞는 결과만 남긴다(다른 세션이거나 결과가 없어졌으면 버린다). */
function matchingResult(result: ResultView | null, session: SessionView): ResultView | null {
  return result !== null && result.session_id === session.session_id && session.has_result ? result : null;
}
