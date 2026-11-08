import type { CloseCheckView, CloseView, HoldReason, InventoryView, ItemKind, Order, OrderStatus } from "../api/types";

export type InventoryCall = "load" | "save" | "check" | "close" | "suggest" | "order" | "refresh" | "resolve";

/** 저장 요청을 낸 양식(성공한 양식만 새 값으로 다시 시작한다). */
export type InventoryForm = "bulk" | "item" | "supplier" | "policy" | "settings" | "receipt" | "auto";
export const INVENTORY_FORMS: readonly InventoryForm[] = ["bulk", "item", "supplier", "policy", "settings", "receipt", "auto"];

export type OrderDraftLine = { itemId: string; quantity: string; unitPrice: string }; // unitPrice: 기준 단가 또는 보류의 새 단가
export type OrderDraft = { requestId: string; supplierId: string; lines: OrderDraftLine[]; repriced: boolean }; // repriced: 보류의 새 단가로 연 초안
export type OrderResultNotice = { status: OrderStatus; holdReason: HoldReason | null };

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
  dirty: boolean; // 마감 탭에 저장하지 않은 입력(수량·조정·날짜)이 있다
  edited: InventoryForm[]; // 저장하지 않은 입력이 있는 양식(그 양식 저장이 성공해야 빠진다)
  saved: Record<InventoryForm, number>; // 양식마다 저장이 성공한 횟수(그 양식의 key)
  order: OrderDraft | null; // 열어 둔 주문 초안(탭을 옮겨도 남는다)
  orderResult: OrderResultNotice | null; // 마지막 주문 응답 안내
  pendingOrderIds: Record<string, string>; // 거래처 id → 응답을 받지 못한 주문의 request_id(다시 열면 같은 번호로, 두 번 주문하지 않게)
};

export type InventoryAction =
  | { type: "requested"; seq: number; kind: InventoryCall; form?: InventoryForm }
  | { type: "failed"; seq: number; message: string }
  | { type: "loaded"; seq: number; view: InventoryView }
  | { type: "checked"; seq: number; check: CloseCheckView }
  | { type: "closed"; seq: number; result: CloseView }
  | { type: "orderOpened"; draft: OrderDraft }
  | { type: "orderQuantityChanged"; itemId: string; quantity: string }
  | { type: "orderLineRemoved"; itemId: string }
  | { type: "orderCancelled" }
  | { type: "ordered"; seq: number; order: Order; view: InventoryView }
  | { type: "orderResultClosed" }
  | { type: "filterChanged"; filter: Partial<InventoryState["filter"]> }
  | { type: "countChanged"; itemId: string; text: string }
  | { type: "anomalyConfirmed"; itemId: string; confirmed: boolean }
  | { type: "adjustmentChanged"; itemId: string; delta: string; reason: string }
  | { type: "closeDateChanged"; date: string }
  | { type: "closeReset" }
  | { type: "edited"; form: InventoryForm }
  | { type: "discarded" }
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
    edited: [],
    saved: { bulk: 0, item: 0, supplier: 0, policy: 0, settings: 0, receipt: 0, auto: 0 },
    order: null,
    orderResult: null,
    pendingOrderIds: {},
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
      return { ...state, inflight: null, toast: action.message, loadFailed, pendingOrderIds: pendingAfterFailure(state) };
    }
    case "loaded":
      if (!isCurrent(state, action.seq)) return state;
      return {
        ...state,
        inflight: null,
        view: action.view,
        loadFailed: false,
        saved: savedAfter(state),
        edited: state.edited.filter((form) => form !== savedForm(state)), // 저장이 끝난 그 양식 입력만 남지 않는다
      };
    case "checked":
      if (!isCurrent(state, action.seq)) return state;
      return {
        ...state,
        inflight: null,
        close: { ...state.close, check: action.check, confirmed: [], adjustments: flaggedOnly(state.close.adjustments, action.check) },
      };
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
    case "orderOpened":
      return { ...state, order: action.draft, orderResult: null };
    case "orderQuantityChanged":
      if (state.order === null) return state;
      return {
        ...state,
        order: { ...state.order, lines: state.order.lines.map((l) => (l.itemId === action.itemId ? { ...l, quantity: action.quantity } : l)) },
      };
    case "orderLineRemoved": {
      if (state.order === null) return state;
      const lines = state.order.lines.filter((l) => l.itemId !== action.itemId);
      return { ...state, order: lines.length === 0 ? null : { ...state.order, lines } };
    }
    case "orderCancelled":
      return { ...state, order: null }; // 기다리는 order 응답은 그래도 받는다(서버가 이미 주문했을 수 있다)
    case "ordered": {
      if (!isCurrent(state, action.seq)) return state;
      const hold = action.view.holds.find((h) => h.order_id === action.order.order_id);
      const { [action.order.supplier_id]: _answered, ...pendingOrderIds } = state.pendingOrderIds;
      return {
        ...state,
        inflight: null,
        view: action.view,
        loadFailed: false,
        order: null,
        orderResult: { status: action.order.status, holdReason: hold?.reason ?? null },
        pendingOrderIds,
      };
    }
    case "orderResultClosed":
      return { ...state, orderResult: null };
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
      return withoutCloseInput(state);
    case "discarded":
      return { ...withoutCloseInput(state), edited: [] };
    case "closeDateChanged":
      return { ...state, dirty: true, close: { ...state.close, date: action.date, check: null, confirmed: [], result: null } };
    case "edited":
      return state.edited.includes(action.form) ? state : { ...state, edited: [...state.edited, action.form] };
    case "toastClosed":
      return { ...state, toast: null };
  }
}

/** 탭을 옮길 때 물어야 하는가: 마감 입력이나 저장하지 않은 양식 입력이 있다. */
export function hasUnsaved(state: InventoryState): boolean {
  return state.dirty || state.edited.length > 0;
}

/** 주문 요청이 실패하면 서버가 받았는지 모른다: 그 초안의 request_id를 거래처별로 기억한다. */
function pendingAfterFailure(state: InventoryState): Record<string, string> {
  if (state.inflight?.kind !== "order" || state.order === null) return state.pendingOrderIds;
  return { ...state.pendingOrderIds, [state.order.supplierId]: state.order.requestId };
}

/** 저장 응답이면 그 요청을 낸 양식의 횟수만 하나 올린다. */
function savedAfter(state: InventoryState): InventoryState["saved"] {
  const form = savedForm(state);
  return form === null ? state.saved : { ...state.saved, [form]: state.saved[form] + 1 };
}

function savedForm(state: InventoryState): InventoryForm | null {
  return state.inflight?.kind === "save" ? state.inflight.form : null;
}

/** 조정은 지금 이상 수량인 품목에만 둔다(화면에 없는 조정을 보내거나 그것 때문에 저장이 막히지 않게). */
function flaggedOnly(adjustments: Record<string, AdjustmentInput>, check: CloseCheckView): Record<string, AdjustmentInput> {
  const flagged = new Set(check.anomalies.map((a) => a.item_id));
  return Object.fromEntries(Object.entries(adjustments).filter(([itemId]) => flagged.has(itemId)));
}

/**
 * 마감 입력을 비운다(날짜는 둔다). 기다리던 검사 응답은 비운 입력의 것이라 더 받지 않는다.
 * 마감 저장 응답은 받는다: 서버는 이미 기록했으니 버리면 화면이 옛 수량을 보이고 다시 마감하면 조정이 두 번 들어간다.
 */
function withoutCloseInput(state: InventoryState): InventoryState {
  const inflight = state.inflight?.kind === "check" ? null : state.inflight;
  return { ...state, inflight, dirty: false, close: { ...EMPTY_CLOSE, date: state.close.date } };
}

function isCurrent(state: InventoryState, seq: number): boolean {
  return state.inflight !== null && state.inflight.seq === seq;
}
