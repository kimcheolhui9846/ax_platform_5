import type { InventoryTab } from "../lib/routes";
import { closeModel, itemsModel, stockModel } from "./screenModel";
import type { InventoryState } from "./state";
import type { InventoryScreenModel } from "./view";

/** 상태 → 그릴 화면. 불러오기 전엔 loading, 처음 불러오기가 실패했으면 unavailable. */
export function inventoryScreen(state: InventoryState, tab: InventoryTab): InventoryScreenModel {
  const { view, filter } = state;
  if (view === null) return { kind: state.loadFailed ? "unavailable" : "loading" };
  switch (tab) {
    case "stock":
      return { kind: "stock", model: stockModel(view, filter), hasItems: view.items.some((v) => !v.item.archived), filter };
    case "close":
      return { kind: "close", model: closeModel(view, state.close, filter), filter };
    case "orders":
    case "auto":
      return { kind: "loading" }; // 준비 중(Task 2·4가 바꾼다)
    case "items":
      return { kind: "items", model: itemsModel(view, state.saved) };
  }
}
