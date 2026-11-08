import { api } from "./client";
import type { ApiResult } from "./client";
import type {
  AutoOrderRequest,
  CloseCheckRequest,
  CloseCheckView,
  CloseRequest,
  CloseView,
  InventorySettingsRequest,
  InventoryView,
  ItemDraft,
  ItemPatch,
  OrderRequest,
  OrderView,
  ReceiptRequest,
  ReorderPolicyRequest,
  SupplierDraft,
  SupplierPatch,
} from "./types";

export type { ApiResult } from "./client";

const BASE = "/api/v1/inventory";

export function getInventory(): Promise<ApiResult<InventoryView>> {
  return api.GET(BASE);
}

export function addItems(items: ItemDraft[]): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/items/bulk`, { body: { items } });
}

export function addItem(item: ItemDraft): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/items`, { body: item });
}

export function updateItem(itemId: string, patch: ItemPatch): Promise<ApiResult<InventoryView>> {
  return api.PATCH(`${BASE}/items/{item_id}`, {
    params: { path: { item_id: itemId } },
    body: patch,
  });
}

export function addSupplier(draft: SupplierDraft): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/suppliers`, { body: draft });
}

export function updateSupplier(supplierId: string, patch: SupplierPatch): Promise<ApiResult<InventoryView>> {
  return api.PATCH(`${BASE}/suppliers/{supplier_id}`, {
    params: { path: { supplier_id: supplierId } },
    body: patch,
  });
}

export function setSettings(body: InventorySettingsRequest): Promise<ApiResult<InventoryView>> {
  return api.PUT(`${BASE}/settings`, { body });
}

export function setPolicy(itemId: string, body: ReorderPolicyRequest): Promise<ApiResult<InventoryView>> {
  return api.PUT(`${BASE}/items/{item_id}/policy`, {
    params: { path: { item_id: itemId } },
    body,
  });
}

export function checkClose(body: CloseCheckRequest): Promise<ApiResult<CloseCheckView>> {
  return api.POST(`${BASE}/closes/check`, { body });
}

export function recordClose(body: CloseRequest): Promise<ApiResult<CloseView>> {
  return api.POST(`${BASE}/closes`, { body });
}

export function suggestPolicy(itemId: string): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/items/{item_id}/policy/suggestion`, {
    params: { path: { item_id: itemId } },
  });
}

export function applySuggestion(itemId: string): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/items/{item_id}/policy/suggestion/apply`, {
    params: { path: { item_id: itemId } },
  });
}

export function placeOrder(body: OrderRequest): Promise<ApiResult<OrderView>> {
  return api.POST(`${BASE}/orders`, { body });
}

export function refreshOrder(orderId: string): Promise<ApiResult<OrderView>> {
  return api.POST(`${BASE}/orders/{order_id}/refresh`, {
    params: { path: { order_id: orderId } },
  });
}

export function receive(orderId: string, body: ReceiptRequest): Promise<ApiResult<OrderView>> {
  return api.POST(`${BASE}/orders/{order_id}/receipts`, {
    params: { path: { order_id: orderId } },
    body,
  });
}

export function resolveHold(holdId: string): Promise<ApiResult<InventoryView>> {
  return api.POST(`${BASE}/holds/{hold_id}/resolve`, {
    params: { path: { hold_id: holdId } },
  });
}

export function setAutoOrder(itemId: string, body: AutoOrderRequest): Promise<ApiResult<InventoryView>> {
  return api.PUT(`${BASE}/items/{item_id}/auto-order`, {
    params: { path: { item_id: itemId } },
    body,
  });
}
