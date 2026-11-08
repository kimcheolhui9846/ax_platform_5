import { addItems, addSupplier, applySuggestion, checkClose, getInventory, recordClose, setPolicy, setSettings, suggestPolicy, updateItem, updateSupplier } from "../api/inventory";
import type { ApiResult } from "../api/inventory";
import type { InventoryView } from "../api/types";
import type { InventoryTab } from "../lib/routes";
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
export function makeInventoryHandlers({ state, tab, run, dispatch, navigate, confirmLeave }: Deps): InventoryHandlers {
  const { counts, adjustments, confirmed } = state.close;
  const entered = Object.fromEntries(Object.entries(counts).filter(([, text]) => text.trim() !== ""));
  return {
    onTab: (next) => {
      if (next === tab) return;
      if (hasUnsaved(state)) {
        if (!confirmLeave()) return;
        dispatch({ type: "discarded" }); // 떠나기로 했으면 마감 입력·양식 입력을 버린다
      }
      navigate(next);
    },
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
    onSuggest: (itemId) =>
      void run({
        kind: "suggest",
        request: () => suggestPolicy(itemId),
        done: (view, seq) => loaded(seq, view),
      }),
  };
}
