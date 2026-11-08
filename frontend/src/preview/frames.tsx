import type { JSX } from "react";

import type { ScreenModel } from "../app/screenModel";
import { AppView, railProps } from "../app/view";
import type { OrderPanel } from "../inventory/orderModel";
import { inventoryScreen, orderPanel } from "../inventory/screen";
import { closeModel, itemsModel, stockModel } from "../inventory/screenModel";
import type { InventoryState } from "../inventory/state";
import { INVENTORY_TAB_LABELS, InventoryView } from "../inventory/view";
import type { InventoryScreenModel } from "../inventory/view";
import { DownloadMenu } from "../components/DownloadMenu";
import { SupplementForm } from "../components/SupplementForm";
import { nextTask } from "../lib/carry";
import { sectionText } from "../lib/document";
import { HOME } from "../lib/routes";
import type { InventoryTab, Route } from "../lib/routes";
import {
  ANSWERED_USER,
  CLOSE_CHECKED,
  CLOSE_DONE,
  CLOSE_INPUT,
  INVENTORY,
  INVENTORY_EMPTY,
  INVENTORY_ORDERS_EMPTY_STATE,
  INVENTORY_ORDERS_STATE,
  ORDER_CONFIRM,
  ORDER_REPRICED,
  ORDER_RESULT,
  SESSION_QUESTION_PRIVATE,
  SESSION_READY_PRIVATE,
  SUPPLEMENT_PRIVATE,
  CONTEXT,
  EVIDENCE_ITEMS,
  FORM,
  LADDER_QUESTION,
  OLD_VERSION,
  PREVIEW_IMAGES,
  PRODUCT,
  PROPOSAL_QUESTION,
  QUESTION,
  REQUEST,
  RESULT,
  RESULT_EVIDENCE,
  RESULT_IMAGE,
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
import { DeleteConfirm, RenameForm } from "../components/WorkItemDialogs";
import { NOOP_HANDLERS, NOOP_INVENTORY_HANDLERS } from "./handlers";

/** 미리보기는 저장소를 쓰지 않아 입력 초안 키는 자리값이다. */
const PREVIEW_KEY = "input:preview";

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
const request: Route = { name: "request", task: PRODUCT.task_type, from: null };
const mode: Route = { name: "mode", task: PRODUCT.task_type, from: null };
const question: Route = { name: "question", sessionId: SESSION_ID };
const confirm: Route = { name: "confirm", sessionId: SESSION_ID };
const failed: Route = { name: "failed", sessionId: SESSION_ID };
const result: Route = { name: "result", sessionId: SESSION_ID };

const ALL = { query: "", kind: "all" } as const;

/** 재고 화면 한 상태. 앱과 같은 InventoryView에 샘플 모델을 직접 넣어 그린다(네트워크 없음). */
function inventoryFrame(id: string, title: string, tab: InventoryTab, model: InventoryScreenModel, panel: OrderPanel = { confirm: null, result: null }): Frame {
  const route: Route = { name: "inventory", tab };
  return {
    id,
    title: `재고 · ${INVENTORY_TAB_LABELS[tab]} · ${title}`,
    render: (mainId) => <InventoryView tab={tab} model={model} panel={panel} busy={null} on={NOOP_INVENTORY_HANDLERS} rail={railProps(route, false, NOOP_HANDLERS)} mainId={mainId} />,
  };
}

/** 상태에서 앱과 같은 순수 함수(inventoryScreen·orderPanel)로 만든 재고 프레임. */
function inventoryStateFrame(id: string, title: string, tab: InventoryTab, state: InventoryState, initialSelected?: string): Frame {
  const model = inventoryScreen(state, tab);
  return inventoryFrame(id, title, tab, model.kind === "auto" ? { ...model, initialSelected } : model, orderPanel(state));
}

/** 갤러리에 그릴 화면 상태. 묶음이 늘 때마다 여기에 상태를 더한다. */
export const FRAMES: Frame[] = [
  frame("home", "홈 · 이어하기", HOME, { kind: "home", tasks: TASKS, sessions: SESSIONS }),
  frame("home-new", "홈 · 처음 방문", HOME, { kind: "home", tasks: TASKS, sessions: [] }),
  frame("request", "01 내 요청", request, { kind: "request", task: PRODUCT, form: FORM, draft: REQUEST, context: null, carryFailed: false, noticeAcknowledged: true }),
  frame(
    "request-context",
    "01 내 요청 · 이전 작업에서 이어가기",
    { name: "request", task: PRODUCT.task_type, from: { sessionId: CONTEXT.session_id, version: CONTEXT.version } },
    { kind: "request", task: PRODUCT, form: FORM, draft: REQUEST, context: CONTEXT, carryFailed: false, noticeAcknowledged: true },
  ),
  frame("request-notice", "01 내 요청 · 외부 전송 안내 확인 전", request, {
    kind: "request",
    task: PRODUCT,
    form: FORM,
    draft: REQUEST,
    context: null,
    carryFailed: false,
    noticeAcknowledged: false,
  }),
  frame("mode", "02 코칭 모드 선택", mode, { kind: "mode", task: PRODUCT, form: FORM, draft: REQUEST, context: null, carryFailed: false, noticeAcknowledged: true }),
  frame("question", "질문 · 기본", question, { kind: "question", task: PRODUCT, session: SESSION_QUESTION, question: QUESTION, draft: "", draftKey: PREVIEW_KEY }),
  frame("question-ladder", "질문 · 다른 예시", question, { kind: "question", task: PRODUCT, session: SESSION_LADDER, question: LADDER_QUESTION, draft: "", draftKey: PREVIEW_KEY }),
  frame("question-proposal", "질문 · AI 후보 제안", question, {
    kind: "question",
    task: PRODUCT,
    session: SESSION_PROPOSAL,
    question: PROPOSAL_QUESTION,
    draft: "",
    draftKey: PREVIEW_KEY,
  }),
  frame("question-private", "질문 · AI에 보내지 않기(체크됨)", question, {
    kind: "question",
    task: PRODUCT,
    session: SESSION_QUESTION_PRIVATE,
    question: QUESTION,
    draft: "",
    draftKey: PREVIEW_KEY,
  }),
  frame(
    "revise",
    "답변 고치기",
    { name: "revise", sessionId: SESSION_ID, questionId: ANSWERED_USER.question.question_id },
    { kind: "revise", task: PRODUCT, session: SESSION_QUESTION, item: ANSWERED_USER, draft: ANSWERED_USER.answer ?? "", draftKey: PREVIEW_KEY },
  ),
  frame("confirm", "03 답변 의미 확인", confirm, { kind: "confirm", task: PRODUCT, session: SESSION_READY }),
  frame("confirm-context", "03 답변 의미 확인 · 가져온 기준", confirm, {
    kind: "confirm",
    task: PRODUCT,
    session: { ...SESSION_READY, context: CONTEXT },
  }),
  frame("confirm-private", "03 답변 의미 확인 · AI에 보내지 않음 표시", confirm, { kind: "confirm", task: PRODUCT, session: SESSION_READY_PRIVATE }),
  frame("generating", "초안 생성 중", confirm, { kind: "generating", task: PRODUCT, session: SESSION_READY }, true),
  frame("failed", "초안 생성 실패", failed, { kind: "failed", task: PRODUCT, session: SESSION_FAILED }),
  frame("failed-with-result", "생성 실패 · 이전 결과 있음", failed, {
    kind: "failed",
    task: PRODUCT,
    session: { ...SESSION_FAILED, has_result: true },
  }),
  frame("result", "결과 문서", result, { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT, images: {} }),
  frame("result-stale", "결과 · 최신 아님", result, { kind: "result", task: PRODUCT, session: SESSION_STALE, result: { ...RESULT, stale: true }, images: {} }),
  frame("result-supplement", "결과 · 미확인 정보 입력(미반영)", result, {
    kind: "result",
    task: PRODUCT,
    session: SESSION_SUPPLEMENT,
    result: RESULT,
    images: {},
  }),
  frame("result-supplemented", "결과 · 보완 정보 반영", result, {
    kind: "result",
    task: PRODUCT,
    session: SESSION_SUPPLEMENTED,
    result: RESULT_SUPPLEMENTED,
    images: {},
  }),
  frame("result-evidence", "결과 · 근거 반영", result, { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT_EVIDENCE, images: {} }),
  frame("result-image", "결과 · 이미지 블록", result, { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT_IMAGE, images: PREVIEW_IMAGES }),
  dialogFrame(
    "result-download",
    "결과 · 문서 내려받기 형식 고르기",
    result,
    { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT, images: {} },
    () => <DownloadMenu full initialOpen onDownload={() => {}} />,
  ),
  dialogFrame(
    "supplement-form",
    "미확인 정보 입력 · 비공개 체크 있음",
    result,
    { kind: "result", task: PRODUCT, session: SESSION_SUPPLEMENT, result: RESULT, images: {} },
    (titleId) => <SupplementForm titleId={titleId} items={SUPPLEMENT_PRIVATE} busy={false} onSave={() => {}} onCancel={() => {}} />,
  ),
  frame(
    "edit",
    "소개 문구 수정",
    { name: "edit", sessionId: SESSION_ID, order: 1 },
    { kind: "edit", task: PRODUCT, session: SESSION_DONE, result: RESULT, section: RESULT.result.sections[0], images: {}, draft: sectionText(RESULT.result.sections[0]), draftKey: PREVIEW_KEY },
  ),
  frame(
    "evidence",
    "근거 자료 검토",
    { name: "evidence", sessionId: SESSION_ID },
    { kind: "evidence", task: PRODUCT, session: SESSION_DONE, result: RESULT, items: EVIDENCE_ITEMS },
  ),
  frame(
    "evidence-applied",
    "근거 검토 · 반영함",
    { name: "evidence", sessionId: SESSION_ID },
    { kind: "evidence", task: PRODUCT, session: SESSION_DONE, result: RESULT_EVIDENCE, items: EVIDENCE_ITEMS },
  ),
  frame(
    "saved",
    "저장 완료 · 버튼 4개(이어가기 포함)",
    { name: "saved", sessionId: SESSION_ID, version: SAVED_VERSION.version.version },
    { kind: "saved", task: PRODUCT, session: SESSION_DONE, version: SAVED_VERSION, images: {}, next: nextTask(TASKS, PRODUCT.task_type) },
  ),
  frame(
    "version",
    "버전 보기 · 지난 버전",
    { name: "version", sessionId: SESSION_ID, version: 1 },
    { kind: "version", task: PRODUCT, session: SESSION_DONE, version: OLD_VERSION, images: {} },
  ),
  frame("work", "내 작업", { name: "work" }, { kind: "work", sessions: SESSIONS }),
  dialogFrame("work-rename", "내 작업 · 이름 바꾸기", { name: "work" }, { kind: "work", sessions: SESSIONS }, (titleId) => (
    <RenameForm titleId={titleId} name={SESSIONS[0].name} busy={false} onSave={() => {}} onCancel={() => {}} />
  )),
  dialogFrame("work-delete", "내 작업 · 삭제 확인", { name: "work" }, { kind: "work", sessions: SESSIONS }, (titleId) => (
    <DeleteConfirm titleId={titleId} name={SESSIONS[0].name} busy={false} onDelete={() => {}} onCancel={() => {}} />
  )),
  frame("work-empty", "내 작업 · 비어 있음", { name: "work" }, { kind: "work", sessions: [] }),
  frame("documents", "결과물", { name: "documents" }, { kind: "documents", sessions: SESSIONS }),
  frame("documents-empty", "결과물 · 비어 있음", { name: "documents" }, { kind: "documents", sessions: [] }),
  frame("guide", "흐름 안내", { name: "guide" }, { kind: "guide" }),
  frame("unavailable", "불러오지 못함", question, { kind: "unavailable" }),
  inventoryFrame("inventory-stock", "품목 있음(부족·미입력·배송 중)", "stock", { kind: "stock", model: stockModel(INVENTORY, ALL), hasItems: true, filter: ALL }),
  inventoryFrame("inventory-stock-empty", "품목 없음", "stock", { kind: "stock", model: stockModel(INVENTORY_EMPTY, ALL), hasItems: false, filter: ALL }),
  inventoryFrame("inventory-close", "수량 입력", "close", { kind: "close", model: closeModel(INVENTORY, CLOSE_INPUT, ALL), filter: ALL }),
  inventoryFrame("inventory-close-check", "이상 수량 확인", "close", { kind: "close", model: closeModel(INVENTORY, CLOSE_CHECKED, ALL), filter: ALL }),
  inventoryFrame("inventory-close-result", "저장 결과·자동 주문", "close", { kind: "close", model: closeModel(INVENTORY, CLOSE_DONE, ALL), filter: ALL }),
  inventoryFrame("inventory-items", "등록·기준·설정", "items", { kind: "items", model: itemsModel(INVENTORY, { bulk: 0, item: 0, supplier: 0, policy: 0, settings: 0, receipt: 0, auto: 0 }) }),
  inventoryStateFrame("inventory-stock-proposal", "제안 묶음", "stock", INVENTORY_ORDERS_STATE),
  inventoryStateFrame("inventory-order-confirm", "주문 확인 카드", "stock", ORDER_CONFIRM),
  inventoryStateFrame("inventory-order-repriced", "새 단가 주문 초안", "orders", ORDER_REPRICED),
  inventoryStateFrame("inventory-order-result", "주문 결과 안내", "stock", ORDER_RESULT),
  inventoryStateFrame("inventory-orders", "보류·주문·입고", "orders", INVENTORY_ORDERS_STATE),
  inventoryStateFrame("inventory-orders-empty", "주문·보류 없음", "orders", INVENTORY_ORDERS_EMPTY_STATE),
  inventoryStateFrame("inventory-auto", "자동 주문 목록", "auto", INVENTORY_ORDERS_STATE),
  inventoryStateFrame("inventory-auto-edit", "자동 주문 편집 카드", "auto", INVENTORY_ORDERS_STATE, "it-2"),
];
