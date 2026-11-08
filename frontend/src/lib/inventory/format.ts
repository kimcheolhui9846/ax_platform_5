import type { AnomalyKind, HoldReason, ItemKind, MockOutcome, OrderStatus, Procurement, StockStatus } from "../../api/types";

export const KIND_LABELS: Record<ItemKind, string> = { finished: "완제품", material: "재료", packaging: "포장재" };
export const STATUS_LABELS: Record<StockStatus, string> = { uncounted: "미입력", short: "부족", in_transit: "배송 중", ok: "충분" };
export const PROCUREMENT_LABELS: Record<Procurement, string> = { purchase: "구매", make: "직접 제작" };
export const ANOMALY_LABELS: Record<AnomalyKind, string> = { increase: "지난번보다 늘었어요", drop: "지난번보다 많이 줄었어요" };

export const HOLD_LABELS: Record<HoldReason, string> = {
  price_changed: "가격이 바뀌었어요",
  limit_exceeded: "한도를 넘었어요",
  out_of_stock: "거래처 재고가 없어요",
  stale_count: "재고 확인이 오래됐어요",
  unknown: "접수 여부를 확인해야 해요",
  address_missing: "배송 주소가 없어요",
};

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  accepted: "주문 접수",
  rejected: "주문 거절",
  unknown: "접수 불명",
  partially_received: "일부 입고",
  received: "입고 완료",
};

/** 문자열 숫자에 천 단위 쉼표를 넣는다. 소수부는 글자 그대로 둔다(계산하지 않는다). */
function grouped(value: string): string {
  const match = /^(-?)(\d+)(\.\d+)?$/.exec(value.trim());
  if (match === null) return value;
  const [, sign, whole, fraction = ""] = match;
  return `${sign}${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}${fraction}`;
}

/** 수량 글. 미입력(null)은 0이 아니다. */
export function quantityText(quantity: string | null, unit: string): string {
  return quantity === null ? "미입력" : `${grouped(quantity)} ${unit}`;
}

export function moneyText(amount: string): string {
  return `${grouped(amount)}원`;
}

export const MOCK_OUTCOME_LABELS: Record<MockOutcome, string> = {
  accept: "접수",
  price_changed: "가격 변동",
  out_of_stock: "품절",
  unknown_then_accept: "접수 불명 뒤 접수",
};
