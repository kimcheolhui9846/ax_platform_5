import { addItems, addSupplier, applySuggestion, checkClose, getInventory, placeOrder, receive, recordClose, refreshOrder, resolveHold, setAutoOrder, setPolicy, setSettings, suggestPolicy, updateItem, updateSupplier } from "../api/inventory";
import type { ApiResult } from "../api/inventory";
import type { AutoOrderRequest, InventoryView } from "../api/types";
import type { InventoryTab } from "../lib/routes";
import { draftFromHold, draftFromProposal, orderConfirmModel, orderProposals } from "./orderModel";
import type { InventoryRequest, InventoryRunner } from "./requests";
import { hasUnsaved } from "./state";
import type { InventoryAction, InventoryForm, InventoryState } from "./state";
import type { InventoryHandlers } from "./view";

type Deps = {
  state: InventoryState;
  tab: InventoryTab; // 지금 보는 탭
  run: InventoryRunner;
  dispatch: (action: InventoryAction) => void;
  navigate: (tab: InventoryTab) => void;
  newRequestId: () => string; // 주문 초안의 request_id(멱등 키)를 만든다
  confirmLeave: () => boolean; // 저장하지 않은 입력을 두고 떠나도 되는지 묻는다(App이 window.confirm을 넘긴다)
};

const loaded = (seq: number, view: InventoryView): InventoryAction => ({ type: "loaded", seq, view });

/** 처음 불러오기·다시 시도. */
export function loadRequest(): InventoryRequest<InventoryView> {
  return { kind: "load", request: getInventory, done: (view, seq) => loaded(seq, view) };
}

function saveRequest(form: InventoryForm, request: () => Promise<ApiResult<InventoryView>>): InventoryRequest<InventoryView> {
  return { kind: "save", form, request, done: (view, seq) => loaded(seq, view) };
}

/** 버튼을 요청 또는 상태 변경으로 바꾼다(코칭 app/handlers.ts와 같은 모양). 저장 요청은 어느 양식인지 함께 알린다. */
export function makeInventoryHandlers({ state, tab, run, dispatch, navigate, newRequestId, confirmLeave }: Deps): InventoryHandlers {
  const { counts, adjustments, confirmed } = state.close;
  const entered = Object.fromEntries(Object.entries(counts).filter(([, text]) => text.trim() !== ""));
  const leave = (go: () => void) => {
    if (hasUnsaved(state)) {
      if (!confirmLeave()) return;
      dispatch({ type: "discarded" }); // 떠나기로 했으면 마감 입력·양식 입력을 버린다
    }
    go();
  };
  const onTab = (next: InventoryTab) => {
    if (next === tab) return;
    leave(() => {
      if (state.close.result !== null) dispatch({ type: "closeReset" }); // 다시 마감 탭에 오면 새 마감으로 시작한다
      navigate(next);
    });
  };
  return {
    onTab,
    onLeave: leave,
    onRetry: () => void run(loadRequest()),
    onFilter: (filter) => dispatch({ type: "filterChanged", filter }),
    onCount: (itemId, text) => dispatch({ type: "countChanged", itemId, text }),
    onConfirm: (itemId, isConfirmed) => dispatch({ type: "anomalyConfirmed", itemId, confirmed: isConfirmed }),
    onAdjust: (itemId, delta, reason) => dispatch({ type: "adjustmentChanged", itemId, delta, reason }),
    onDate: (date) => dispatch({ type: "closeDateChanged", date }),
    onReset: () => dispatch({ type: "closeReset" }),
    onOpenStock: () => navigate("stock"),
    onEdited: (form) => dispatch({ type: "edited", form }),
    onCheck: () =>
      void run({
        kind: "check",
        request: () => checkClose({ counts: entered }),
        done: (check, seq) => ({ type: "checked", seq, check }),
      }),
    onSave: (date) =>
      void run({
        kind: "close",
        request: () =>
          recordClose({
            close_date: date,
            counts: entered,
            adjustments: Object.entries(adjustments)
              .filter(([, a]) => a.delta.trim() !== "" && a.reason.trim() !== "")
              .map(([item_id, a]) => ({ item_id, delta: a.delta.trim(), reason: a.reason.trim() })),
            confirmed,
          }),
        done: (result, seq) => ({ type: "closed", seq, result }),
      }),
    onCreateItems: (drafts) => void run(saveRequest("bulk", () => addItems(drafts))),
    onUpdateItem: (itemId, patch) => void run(saveRequest("item", () => updateItem(itemId, patch))),
    onCreateSupplier: (draft) => void run(saveRequest("supplier", () => addSupplier(draft))),
    onUpdateSupplier: (id, patch) => void run(saveRequest("supplier", () => updateSupplier(id, patch))),
    onSavePolicy: (itemId, request) => void run(saveRequest("policy", () => setPolicy(itemId, request))),
    onApplySuggestion: (itemId) => void run(saveRequest("policy", () => applySuggestion(itemId))),
    onSaveSettings: (request) => void run(saveRequest("settings", () => setSettings(request))),
    onOpenOrder: (supplierId) => {
      const group = state.view === null ? undefined : orderProposals(state.view).find((g) => g.supplierId === supplierId);
      if (group !== undefined) dispatch({ type: "orderOpened", draft: draftFromProposal(group, newRequestId()) });
    },
    onOrderQuantity: (itemId, quantity) => dispatch({ type: "orderQuantityChanged", itemId, quantity }),
    onOrderRemoveLine: (itemId) => dispatch({ type: "orderLineRemoved", itemId }),
    onOrderCancel: () => dispatch({ type: "orderCancelled" }),
    onOrderResultClose: () => dispatch({ type: "orderResultClosed" }),
    onPlaceOrder: () => {
      const { view, order } = state;
      if (view === null || order === null || !orderConfirmModel(view, order).canSubmit) return;
      void run({
        kind: "order",
        request: () =>
          placeOrder({
            request_id: order.requestId,
            lines: order.lines.map((l) => ({
              item_id: l.itemId,
              quantity: l.quantity.trim(),
              ...(order.repriced ? { unit_price: l.unitPrice } : {}),
            })),
          }),
        done: (r, seq) => ({ type: "ordered", seq, order: r.order, view: r.inventory }),
      });
    },
    onRefreshOrder: (orderId) =>
      void run({ kind: "refresh", request: () => refreshOrder(orderId), done: (r, seq) => loaded(seq, r.inventory) }),
    onReceive: (orderId, lines) =>
      void run({ kind: "save", form: "receipt", request: () => receive(orderId, { lines }), done: (r, seq) => loaded(seq, r.inventory) }),
    onResolveHold: (holdId) => void run({ kind: "resolve", request: () => resolveHold(holdId), done: (view, seq) => loaded(seq, view) }),
    onReviewHold: (holdId) => {
      const draft = state.view === null ? null : draftFromHold(state.view, holdId, newRequestId());
      if (draft !== null) dispatch({ type: "orderOpened", draft });
    },
    onSaveAutoOrder: (itemId, request: AutoOrderRequest) => void run(saveRequest("auto", () => setAutoOrder(itemId, request))),
    onOpenOrders: () => onTab("orders"),
    onSuggest: (itemId) =>
      void run({
        kind: "suggest",
        request: () => suggestPolicy(itemId),
        done: (view, seq) => loaded(seq, view),
      }),
  };
}
