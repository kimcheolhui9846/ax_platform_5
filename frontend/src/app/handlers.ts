import type { ApiResult } from "../api/client";
import {
  applyEvidence as applyEvidenceRequest,
  continueSession,
  clearContext as clearContextRequest,
  createSession,
  editResultSection,
  generateResult,
  reviseAnswer,
  saveSupplements as saveSupplementsRequest,
  saveVersion as saveVersionRequest,
  showOriginalQuestion,
  submitAnswer,
} from "../api/coaching";
import type { AnswerBody, SessionView } from "../api/types";
import type { DocumentFile } from "../lib/documentHtml";
import { EVIDENCE_APPLIED_NOTICE, versionBeforeEvidence } from "../lib/evidence";
import { HOME } from "../lib/routes";
import type { CarryScreen, Route } from "../lib/routes";
import { resumeRoute } from "../lib/sessions";
import { PLAIN } from "./requests";
import type { Runner } from "./requests";
import type { Action, AppState } from "./state";
import type { Handlers } from "./view";

export const NOTHING_LEFT_NOTICE = "더 물어볼 질문이 없어요.";
export const DOWNLOADED_NOTICE = "문서를 내려받았어요.";
export const SUPPLEMENTS_SAVED_NOTICE = "입력 내용을 저장했어요. ‘초안에 반영’을 눌러 적용해 주세요.";
export const SUPPLEMENTS_APPLIED_NOTICE = "입력한 정보를 초안의 보완 기준에 반영했어요.";
export const CONTEXT_CLEARED_NOTICE = "가져온 내용을 뺐어요.";
export const SECTION_EDITED_NOTICE = "문구를 반영했어요. 다른 기준과 검토 기록은 그대로예요.";

/** [순수] 답이 바뀐 세션의 다음 화면. 걸린 질문이 있으면 질문, 없으면 답변 확인. */
export function routeAfterSession(session: SessionView): Route {
  return session.next_question
    ? { name: "question", sessionId: session.session_id }
    : { name: "confirm", sessionId: session.session_id };
}

type Deps = {
  state: Pick<AppState, "session" | "drafts" | "result">;
  /** 요청·모드 화면이면 그 화면(과제·이어 가는 출처). 아니면 null. */
  carryScreen: CarryScreen | null;
  run: Runner;
  dispatch: (action: Action) => void;
  saveDraft: (task: string, text: string) => void;
  saveFile: (file: DocumentFile) => void;
};

/** 화면 버튼 → 화면 이동(dispatch) 또는 API 요청(run). 상태는 리듀서만 바꾼다. */
export function makeHandlers({ state, carryScreen, run, dispatch, saveDraft, saveFile }: Deps): Handlers {
  const session = state.session;
  const from = carryScreen?.from ?? null;
  const go = (route: Route) => dispatch({ type: "navigated", route });

  /** 세션을 바꾸는 요청. 응답 세션의 다음 화면(질문 또는 답변 확인)으로 간다. */
  const moveOn = (request: () => Promise<ApiResult<SessionView>>) =>
    void run({
      request,
      done: (next, seq) => ({ type: "sessionLoaded", seq, session: next, next: routeAfterSession(next), notice: null }),
      ...PLAIN,
    });

  const answer = (body: AnswerBody) => {
    const question = session?.next_question;
    if (session && question) moveOn(() => submitAnswer(session.session_id, question.question_id, body));
  };

  /** 지금 정보로 결과를 만들고 결과 화면으로 간다. 성공이든 실패든 서버 세션이 바뀌었으니 다시 받는다. */
  const generateWith = (notice: string | null) => {
    if (!session) return;
    const sessionId = session.session_id;
    void run({
      request: () => generateResult(sessionId),
      done: (result, seq) => ({
        type: "resultLoaded",
        seq,
        result,
        next: { name: "result", sessionId },
        outdatesSession: true,
        notice,
      }),
      ...PLAIN,
      generating: true,
      failedRoute: { name: "failed", sessionId },
      outdatesSessionOnFail: true,
    });
  };

  return {
    navigate: (key) => go(key === "home" ? HOME : key === "work" ? { name: "work" } : { name: "documents" }),
    guide: () => go({ name: "guide" }),
    goHome: () => go(HOME),
    retry: () => dispatch({ type: "retried" }),
    start: (task) => go({ name: "request", task, from: null }),
    changeDraft: (task, text) => {
      dispatch({ type: "draftChanged", task, text });
      saveDraft(task, text);
    },
    submitRequest: (task) => go({ name: "mode", task, from }),
    editRequest: (task) => go({ name: "request", task, from }),
    pickMode: (task, mode) => moveOn(() => createSession(task, state.drafts[task] ?? "", mode, from)),
    startNext: (task, source) => go({ name: "request", task, from: source }),
    dropCarry: (task) => {
      if (carryScreen !== null && carryScreen.task === task) go({ name: carryScreen.screen, task, from: null });
    },
    clearContext: () => {
      if (!session) return;
      const sessionId = session.session_id;
      void run({
        request: () => clearContextRequest(sessionId),
        done: (next, seq) => ({ type: "sessionLoaded", seq, session: next, next: null, notice: CONTEXT_CLEARED_NOTICE }),
        ...PLAIN,
      });
    },
    answer,
    example: (action) => {
      if (action === "easier") answer({ answer_type: "easier" });
      else if (session) moveOn(() => showOriginalQuestion(session.session_id));
    },
    earlyDraft: () => {
      if (session) go({ name: "confirm", sessionId: session.session_id });
    },
    edit: (questionId) => {
      if (session) go({ name: "revise", sessionId: session.session_id, questionId });
    },
    revise: (questionId, body) => {
      if (session) moveOn(() => reviseAnswer(session.session_id, questionId, body));
    },
    backToQuestions: () => {
      if (session) go(routeAfterSession(session));
    },
    generate: () => generateWith(null),
    showResult: () => {
      if (session) go({ name: "result", sessionId: session.session_id });
    },
    confirm: () => {
      if (session) go({ name: "confirm", sessionId: session.session_id });
    },
    continueQuestions: () => {
      if (!session) return;
      void run({
        request: () => continueSession(session.session_id),
        done: (next, seq) => ({
          type: "sessionLoaded",
          seq,
          session: next,
          next: next.next_question ? routeAfterSession(next) : null,
          notice: next.next_question ? null : NOTHING_LEFT_NOTICE,
        }),
        ...PLAIN,
      });
    },
    resume: (summary) => go(resumeRoute(summary)),
    openVersion: (sessionId, version) => go({ name: "version", sessionId, version }),
    saveVersion: () => {
      const result = state.result;
      if (!session || !result) return;
      const sessionId = session.session_id;
      const number = result.version.version;
      void run({
        request: () => saveVersionRequest(sessionId, number),
        done: (version, seq) => ({ type: "versionSaved", seq, version, next: { name: "saved", sessionId, version: number } }),
        ...PLAIN,
      });
    },
    saveSupplements: (values) => {
      if (!session) return;
      const sessionId = session.session_id;
      void run({
        request: () => saveSupplementsRequest(sessionId, values),
        done: (next, seq) => ({ type: "sessionLoaded", seq, session: next, next: null, notice: SUPPLEMENTS_SAVED_NOTICE }),
        ...PLAIN,
      });
    },
    applySupplements: () => generateWith(SUPPLEMENTS_APPLIED_NOTICE),
    editSection: (order) => {
      if (session) go({ name: "edit", sessionId: session.session_id, order });
    },
    submitEdit: (order, text) => {
      if (!session) return;
      const sessionId = session.session_id;
      void run({
        request: () => editResultSection(sessionId, order, text),
        // 문구 수정은 세션(답·보완 정보·최신 여부)을 바꾸지 않는다
        done: (result, seq) => ({
          type: "resultLoaded",
          seq,
          result,
          next: { name: "result", sessionId },
          outdatesSession: false,
          notice: SECTION_EDITED_NOTICE,
        }),
        ...PLAIN,
      });
    },
    reviewEvidence: () => {
      if (session) go({ name: "evidence", sessionId: session.session_id });
    },
    applyEvidence: (sourceId) => {
      if (!session) return;
      const sessionId = session.session_id;
      void run({
        request: () => applyEvidenceRequest(sessionId, sourceId),
        // 근거 반영은 세션(답·보완 정보·최신 여부)을 바꾸지 않는다
        done: (result, seq) => ({
          type: "resultLoaded",
          seq,
          result,
          next: { name: "result", sessionId },
          outdatesSession: false,
          notice: EVIDENCE_APPLIED_NOTICE,
        }),
        ...PLAIN,
      });
    },
    openBeforeEvidence: () => {
      const before = state.result ? versionBeforeEvidence(state.result.version) : null;
      if (session && before !== null) go({ name: "version", sessionId: session.session_id, version: before });
    },
    download: (file) => {
      saveFile(file);
      dispatch({ type: "noticed", message: DOWNLOADED_NOTICE });
    },
  };
}
