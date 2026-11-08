import type { AnomalyKind, HoldReason, ItemKind, MockOutcome, OrderOrigin, OrderStatus, Procurement, StockStatus } from "../../api/types";

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

/** 수량 글. 미입력(null)은 0이 아니다. 소수 끝의 0(서버의 자리 맞춤 "30.00")은 뺀다. */
export function quantityText(quantity: string | null, unit: string): string {
  return quantity === null ? "미입력" : `${grouped(withoutTrailingZeros(quantity))} ${unit}`;
}

function withoutTrailingZeros(value: string): string {
  return /^-?\d+\.\d+$/.test(value.trim()) ? value.trim().replace(/\.?0+$/, "") : value;
}

/** 금액 글. 소수가 모두 0("4500.00")이면 뺀다(원 단위는 보통 소수가 없다). */
export function moneyText(amount: string): string {
  return `${grouped(amount.trim().replace(/\.0+$/, ""))}원`;
}

export const MOCK_OUTCOME_LABELS: Record<MockOutcome, string> = {
  accept: "접수",
  price_changed: "가격 변동",
  out_of_stock: "품절",
  unknown_then_accept: "접수 불명 뒤 접수",
};

/** 기계의 로컬 날짜를 YYYY-MM-DD로(마감 날짜 기본값). */
export function localDateText(date: Date): string {
  const two = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`;
}

export const ORIGIN_LABELS: Record<OrderOrigin, string> = { manual: "직접 주문", auto: "자동 주문" };

/** 음수 아닌 십진 글 → 정수 부분(자릿수만큼 10을 곱한 값)과 소수 자릿수. 숫자 글이 아니면 null. */
function scaled(text: string): { n: bigint; scale: number } | null {
  const match = /^(\d+)(?:\.(\d+))?$/.exec(text.trim());
  if (match === null) return null;
  const fraction = match[2] ?? "";
  return { n: BigInt(match[1] + fraction), scale: fraction.length };
}

/** 센트(정수) → "12500.00". */
function centsText(cents: bigint): string {
  const s = cents.toString().padStart(3, "0");
  return `${s.slice(0, -2)}.${s.slice(-2)}`;
}

/** 수량 × 단가를 0.01로 반올림(절반 올림). 정수로 계산해 부동소수 오차가 없다. 숫자 글이 아니면 null. */
export function lineAmount(quantity: string, unitPrice: string): string | null {
  const q = scaled(quantity);
  const p = scaled(unitPrice);
  if (q === null || p === null) return null;
  const divisor = 10n ** BigInt(q.scale + p.scale);
  return centsText((2n * q.n * p.n * 100n + divisor) / (2n * divisor));
}

/** 금액 글(소수 둘째 자리까지)의 합. */
export function sumAmounts(amounts: string[]): string {
  let cents = 0n;
  for (const amount of amounts) {
    const a = scaled(amount);
    if (a === null) continue;
    cents += (2n * a.n * 100n + 10n ** BigInt(a.scale)) / (2n * 10n ** BigInt(a.scale));
  }
  return centsText(cents);
}

/** 주문 수량 − 입고 수량(서버 값의 차, 0 아래로는 내려가지 않는다). 소수 끝의 0은 뺀다. */
export function remainingQuantity(ordered: string, received: string): string {
  const o = scaled(ordered);
  const r = scaled(received);
  if (o === null || r === null) return "0";
  const scale = Math.max(o.scale, r.scale);
  const up = (v: { n: bigint; scale: number }) => v.n * 10n ** BigInt(scale - v.scale);
  const diff = up(o) - up(r);
  if (diff <= 0n) return "0";
  const s = diff.toString().padStart(scale + 1, "0");
  const whole = s.slice(0, s.length - scale);
  const fraction = s.slice(s.length - scale).replace(/0+$/, "");
  return fraction === "" ? whole : `${whole}.${fraction}`;
}
