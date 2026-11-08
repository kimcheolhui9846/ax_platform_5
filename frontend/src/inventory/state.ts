import type { CloseCheckView, CloseView, InventoryView, ItemKind } from "../api/types";

export type InventoryCall = "load" | "save" | "check" | "close" | "suggest";

/** 저장 요청을 낸 양식(성공한 양식만 새 값으로 다시 시작한다). */
export type InventoryForm = "bulk" | "item" | "supplier" | "policy" | "settings";
export const INVENTORY_FORMS: readonly InventoryForm[] = ["bulk", "item", "supplier", "policy", "settings"];

export type AdjustmentInput = { delta: string; reason: string };

export type InventoryState = {
  view: InventoryView | null; // 마지막으로 받은 재고 전체
  loadFailed: boolean; // 처음 불러오기 실패(다시 시도 버튼)
  inflight: { seq: number; kind: InventoryCall; form: InventoryForm | null } | null; // 지금 기다리는 요청 하나
  toast: string | null;
  filter: { query: string; kind: ItemKind | "all" }; // 현황·마감 공용 검색·분류
  close: {
    counts: Record<string, string>; // 품목 id → 입력 글(빈칸 = 미입력)
    check: CloseCheckView | null; // 검사 결과(이상 수량)
    confirmed: string[]; // 이상 수량을 맞다고 확인한 품목
    adjustments: Record<string, AdjustmentInput>;
    result: CloseView | null; // 저장 결과(자동 주문 요약)
    date: string; // 고른 마감 날짜 YYYY-MM-DD
  };
  dirty: boolean; // 저장하지 않은 입력이 있다(탭 옮길 때 확인)
  saved: Record<InventoryForm, number>; // 양식마다 저장이 성공한 횟수(그 양식의 key)
};

export type InventoryAction =
  | { type: "requested"; seq: number; kind: InventoryCall; form?: InventoryForm }
  | { type: "failed"; seq: number; message: string }
  | { type: "loaded"; seq: number; view: InventoryView }
  | { type: "checked"; seq: number; check: CloseCheckView }
  | { type: "closed"; seq: number; result: CloseView }
  | { type: "filterChanged"; filter: Partial<InventoryState["filter"]> }
  | { type: "countChanged"; itemId: string; text: string }
  | { type: "anomalyConfirmed"; itemId: string; confirmed: boolean }
  | { type: "adjustmentChanged"; itemId: string; delta: string; reason: string }
  | { type: "closeDateChanged"; date: string }
  | { type: "closeReset" }
  | { type: "edited" }
  | { type: "saved" }
  | { type: "toastClosed" };

export const EMPTY_CLOSE: InventoryState["close"] = { counts: {}, check: null, confirmed: [], adjustments: {}, result: null, date: "" };

/** today는 마감 날짜 기본값(호출하는 쪽이 정한다. reducer는 시계를 보지 않는다). */
export function initialInventoryState(today = ""): InventoryState {
  return {
    view: null,
    loadFailed: false,
    inflight: null,
    toast: null,
    filter: { query: "", kind: "all" },
    close: { ...EMPTY_CLOSE, date: today },
    dirty: false,
    saved: { bulk: 0, item: 0, supplier: 0, policy: 0, settings: 0 },
  };
}

/** 재고 상태는 여기서만 바뀐다(순수). 응답은 지금 기다리는 요청(inflight.seq)의 것일 때만 받는다. */
export function inventoryReducer(state: InventoryState, action: InventoryAction): InventoryState {
  switch (action.type) {
    case "requested":
      return { ...state, inflight: { seq: action.seq, kind: action.kind, form: action.form ?? null }, toast: null };
    case "failed": {
      const inflight = state.inflight;
      if (inflight === null || inflight.seq !== action.seq) return state;
      const loadFailed = inflight.kind === "load" && state.view === null ? true : state.loadFailed;
      return { ...state, inflight: null, toast: action.message, loadFailed };
    }
    case "loaded":
      if (!isCurrent(state, action.seq)) return state;
      return {
        ...state,
        inflight: null,
        view: action.view,
        loadFailed: false,
        saved: savedAfter(state),
        dirty: state.inflight?.kind === "save" ? hasCloseInput(state) : state.dirty, // 저장이 끝난 양식 입력은 남지 않는다
      };
    case "checked":
      if (!isCurrent(state, action.seq)) return state;
      return { ...state, inflight: null, close: { ...state.close, check: action.check, confirmed: [] } };
    case "closed":
      if (!isCurrent(state, action.seq)) return state;
      return {
        ...state,
        inflight: null,
        view: action.result.inventory,
        loadFailed: false,
        dirty: false,
        close: { ...EMPTY_CLOSE, date: state.close.date, result: action.result },
      };
    case "filterChanged":
      return { ...state, filter: { ...state.filter, ...action.filter } };
    case "countChanged": {
      const counts = { ...state.close.counts };
      if (action.text === "") delete counts[action.itemId];
      else counts[action.itemId] = action.text;
      return { ...state, dirty: true, close: { ...state.close, counts, check: null, confirmed: [], result: null } };
    }
    case "anomalyConfirmed": {
      const rest = state.close.confirmed.filter((id) => id !== action.itemId);
      const confirmed = action.confirmed ? [...rest, action.itemId] : rest;
      return { ...state, close: { ...state.close, confirmed } };
    }
    case "adjustmentChanged":
      return {
        ...state,
        dirty: true,
        close: { ...state.close, adjustments: { ...state.close.adjustments, [action.itemId]: { delta: action.delta, reason: action.reason } } },
      };
    case "closeReset":
      return { ...state, dirty: false, close: { ...EMPTY_CLOSE, date: state.close.date } };
    case "closeDateChanged":
      return { ...state, dirty: true, close: { ...state.close, date: action.date, check: null, confirmed: [], result: null } };
    case "edited":
      return { ...state, dirty: true };
    case "saved":
      return { ...state, dirty: false };
    case "toastClosed":
      return { ...state, toast: null };
  }
}

/** 저장 응답이면 그 요청을 낸 양식의 횟수만 하나 올린다. */
function savedAfter(state: InventoryState): InventoryState["saved"] {
  const form = state.inflight?.kind === "save" ? state.inflight.form : null;
  return form === null ? state.saved : { ...state.saved, [form]: state.saved[form] + 1 };
}

function isCurrent(state: InventoryState, seq: number): boolean {
  return state.inflight !== null && state.inflight.seq === seq;
}

/** 마감 탭에 아직 저장하지 않은 입력(센 수량·조정)이 있는가. */
function hasCloseInput(state: InventoryState): boolean {
  return Object.keys(state.close.counts).length > 0 || Object.keys(state.close.adjustments).length > 0;
}
