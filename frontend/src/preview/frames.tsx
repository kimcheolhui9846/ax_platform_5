import type { JSX } from "react";

import type { ScreenModel } from "../app/screenModel";
import { AppView } from "../app/view";
import { SupplementForm } from "../components/SupplementForm";
import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import {
  ANSWERED_USER,
  FORM,
  LADDER_QUESTION,
  OLD_VERSION,
  PRODUCT,
  PROPOSAL_QUESTION,
  QUESTION,
  REQUEST,
  RESULT,
  RESULT_SUPPLEMENTED,
  SAVED_VERSION,
  SESSIONS,
  SESSION_DONE,
  SESSION_FAILED,
  SESSION_LADDER,
  SESSION_PROPOSAL,
  SESSION_QUESTION,
  SESSION_READY,
  SESSION_STALE,
  SESSION_SUPPLEMENT,
  SESSION_SUPPLEMENTED,
  TASKS,
} from "./fixtures";
import { NOOP_HANDLERS } from "./handlers";

/** render는 프레임마다 다른 본문 id를 받는다(한 페이지에 프레임이 여럿이라 id가 겹치지 않게). */
export type Frame = { id: string; title: string; render: (mainId: string) => JSX.Element };

/** 프레임 크기 이름. 폭은 tokens.css의 --preview-desktop·--preview-mobile이 정한다. */
export const FRAME_SIZES = ["desktop", "mobile"] as const;

function frame(id: string, title: string, route: Route, model: ScreenModel, busy = false): Frame {
  return { id, title, render: (mainId) => <AppView route={route} model={model} busy={busy} on={NOOP_HANDLERS} mainId={mainId} /> };
}

/** 대화상자를 연 화면. 갤러리에서는 대화상자를 열 수 없어서 같은 양식을 대화상자 표면(.dialog)에 담아 겹쳐 그린다. */
function dialogFrame(id: string, title: string, route: Route, model: ScreenModel, dialog: (titleId: string) => JSX.Element): Frame {
  return {
    id,
    title,
    render: (mainId) => (
      <div className="gallery-dialog-frame">
        <div className="gallery-dialog-base">
          <AppView route={route} model={model} busy={false} on={NOOP_HANDLERS} mainId={mainId} />
        </div>
        <div className="dialog gallery-dialog" role="dialog" aria-labelledby={`${mainId}-dialog`}>
          {dialog(`${mainId}-dialog`)}
        </div>
      </div>
    ),
  };
}

const SESSION_ID = SESSION_QUESTION.session_id;
const request: Route = { name: "request", task: PRODUCT.task_type };
const mode: Route = { name: "mode", task: PRODUCT.task_type };
const question: Route = { name: "question", sessionId: SESSION_ID };
const confirm: Route = { name: "confirm", sessionId: SESSION_ID };
const result: Route = { name: "result", sessionId: SESSION_ID };

/** 갤러리에 그릴 화면 상태. 묶음이 늘 때마다 여기에 상태를 더한다. */
export const FRAMES: Frame[] = [
  frame("home", "홈 · 이어하기", HOME, { kind: "home", tasks: TASKS, sessions: SESSIONS }),
  frame("home-new", "홈 · 처음 방문", HOME, { kind: "home", tasks: TASKS, sessions: [] }),
  frame("request", "01 내 요청", request, { kind: "request", task: PRODUCT, form: FORM, draft: REQUEST }),
  frame("mode", "02 코칭 모드 선택", mode, { kind: "mode", task: PRODUCT, form: FORM, draft: REQUEST }),
  frame("question", "질문 · 기본", question, { kind: "question", task: PRODUCT, session: SESSION_QUESTION, question: QUESTION }),
  frame("question-ladder", "질문 · 다른 예시", question, { kind: "question", task: PRODUCT, session: SESSION_LADDER, question: LADDER_QUESTION }),
  frame("question-proposal", "질문 · AI 후보 제안", question, {
    kind: "question",
    task: PRODUCT,
    session: SESSION_PROPOSAL,
    question: PROPOSAL_QUESTION,
  }),
  frame(
    "revise",
    "답변 고치기",
    { name: "revise", sessionId: SESSION_ID, questionId: ANSWERED_USER.question.question_id },
    { kind: "revise", task: PRODUCT, session: SESSION_QUESTION, item: ANSWERED_USER },
  ),
  frame("confirm", "03 답변 의미 확인", confirm, { kind: "confirm", task: PRODUCT, session: SESSION_READY }),
  frame("confirm-generating", "답변 확인 · 초안 만드는 중", confirm, { kind: "confirm", task: PRODUCT, session: SESSION_READY }, true),
  frame("confirm-failed", "답변 확인 · 생성 실패", confirm, { kind: "confirm", task: PRODUCT, session: SESSION_FAILED }),
  frame("result", "결과 문서", result, { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT }),
  frame("result-stale", "결과 · 최신 아님", result, { kind: "result", task: PRODUCT, session: SESSION_STALE, result: { ...RESULT, stale: true } }),
  frame("result-supplement", "결과 · 미확인 정보 입력(미반영)", result, {
    kind: "result",
    task: PRODUCT,
    session: SESSION_SUPPLEMENT,
    result: RESULT,
  }),
  frame("result-supplemented", "결과 · 보완 정보 반영", result, {
    kind: "result",
    task: PRODUCT,
    session: SESSION_SUPPLEMENTED,
    result: RESULT_SUPPLEMENTED,
  }),
  dialogFrame(
    "supplement-form",
    "미확인 정보 입력",
    result,
    { kind: "result", task: PRODUCT, session: SESSION_SUPPLEMENT, result: RESULT },
    (titleId) => <SupplementForm titleId={titleId} items={SESSION_SUPPLEMENT.supplements} busy={false} onSave={() => {}} onCancel={() => {}} />,
  ),
  frame(
    "edit",
    "소개 문구 수정",
    { name: "edit", sessionId: SESSION_ID, order: 1 },
    { kind: "edit", task: PRODUCT, session: SESSION_DONE, result: RESULT, section: RESULT.result.sections[0] },
  ),
  frame(
    "saved",
    "저장 완료",
    { name: "saved", sessionId: SESSION_ID, version: SAVED_VERSION.version.version },
    { kind: "saved", task: PRODUCT, session: SESSION_DONE, version: SAVED_VERSION },
  ),
  frame(
    "version",
    "버전 보기 · 지난 버전",
    { name: "version", sessionId: SESSION_ID, version: 1 },
    { kind: "version", task: PRODUCT, session: SESSION_DONE, version: OLD_VERSION },
  ),
  frame("work", "내 작업", { name: "work" }, { kind: "work", sessions: SESSIONS }),
  frame("work-empty", "내 작업 · 비어 있음", { name: "work" }, { kind: "work", sessions: [] }),
  frame("documents", "결과물", { name: "documents" }, { kind: "documents", sessions: SESSIONS }),
  frame("documents-empty", "결과물 · 비어 있음", { name: "documents" }, { kind: "documents", sessions: [] }),
  frame("guide", "흐름 안내", { name: "guide" }, { kind: "guide" }),
  frame("unavailable", "불러오지 못함", question, { kind: "unavailable" }),
];
