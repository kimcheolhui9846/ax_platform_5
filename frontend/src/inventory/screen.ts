import type { InventoryTab } from "../lib/routes";
import { closeModel, itemsModel, stockModel } from "./screenModel";
import { autoModel, holdRows, orderCards, orderConfirmModel, orderResultText } from "./orderModel";
import type { OrderPanel } from "./orderModel";
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
      return { kind: "orders", orders: orderCards(view), holds: holdRows(view), saved: state.saved.receipt };
    case "auto":
      return { kind: "auto", model: autoModel(view), items: view.items, saved: state.saved.auto };
    case "items":
      return { kind: "items", model: itemsModel(view, state.saved) };
  }
}

/** 탭 줄 아래에 모든 탭에서 보이는 주문 확인 카드와 결과 안내. */
export function orderPanel(state: InventoryState): OrderPanel {
  const { view, order, orderResult } = state;
  return {
    confirm: view === null || order === null ? null : orderConfirmModel(view, order),
    result: orderResult === null ? null : orderResultText(orderResult),
  };
}
