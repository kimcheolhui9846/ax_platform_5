import type { ApiResult } from "../api/client";
import {
  continueSession,
  createSession,
  generateResult,
  reviseAnswer,
  saveVersion as saveVersionRequest,
  showOriginalQuestion,
  submitAnswer,
} from "../api/coaching";
import type { AnswerBody, SessionView } from "../api/types";
import type { DocumentFile } from "../lib/documentHtml";
import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import { resumeRoute } from "../lib/sessions";
import type { Runner } from "./requests";
import type { Action, AppState } from "./state";
import type { Handlers } from "./view";

export const NOTHING_LEFT_NOTICE = "더 물어볼 질문이 없어요.";
export const DOWNLOADED_NOTICE = "문서를 내려받았어요.";

/** [순수] 답이 바뀐 세션의 다음 화면. 걸린 질문이 있으면 질문, 없으면 답변 확인. */
export function routeAfterSession(session: SessionView): Route {
  return session.next_question
    ? { name: "question", sessionId: session.session_id }
    : { name: "confirm", sessionId: session.session_id };
}

type Deps = {
  state: Pick<AppState, "session" | "drafts" | "result">;
  run: Runner;
  dispatch: (action: Action) => void;
  saveDraft: (task: string, text: string) => void;
  saveFile: (file: DocumentFile) => void;
};

/** 화면 버튼 → 화면 이동(dispatch) 또는 API 요청(run). 상태는 리듀서만 바꾼다. */
export function makeHandlers({ state, run, dispatch, saveDraft, saveFile }: Deps): Handlers {
  const session = state.session;
  const go = (route: Route) => dispatch({ type: "navigated", route });

  /** 세션을 바꾸는 요청. 응답 세션의 다음 화면(질문 또는 답변 확인)으로 간다. */
  const moveOn = (request: () => Promise<ApiResult<SessionView>>) =>
    void run({
      request,
      done: (next, seq) => ({ type: "sessionLoaded", seq, session: next, next: routeAfterSession(next), notice: null }),
      load: null,
      outdatesSessionOnFail: false,
    });

  const answer = (body: AnswerBody) => {
    const question = session?.next_question;
    if (session && question) moveOn(() => submitAnswer(session.session_id, question.question_id, body));
  };

  return {
    navigate: (key) => go(key === "home" ? HOME : key === "work" ? { name: "work" } : { name: "documents" }),
    guide: () => go({ name: "guide" }),
    goHome: () => go(HOME),
    retry: () => dispatch({ type: "retried" }),
    start: (task) => go({ name: "request", task }),
    changeDraft: (task, text) => {
      dispatch({ type: "draftChanged", task, text });
      saveDraft(task, text);
    },
    submitRequest: (task) => go({ name: "mode", task }),
    editRequest: (task) => go({ name: "request", task }),
    pickMode: (task, mode) => moveOn(() => createSession(task, state.drafts[task] ?? "", mode)),
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
    generate: () => {
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
        }),
        load: null,
        outdatesSessionOnFail: true,
      });
    },
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
        load: null,
        outdatesSessionOnFail: false,
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
        done: (version, seq) => ({ type: "versionSaved", seq, version, next: { name: "saved", sessionId } }),
        load: null,
        outdatesSessionOnFail: false,
      });
    },
    download: (file) => {
      saveFile(file);
      dispatch({ type: "noticed", message: DOWNLOADED_NOTICE });
    },
  };
}
