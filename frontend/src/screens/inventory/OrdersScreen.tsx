import { useState } from "react";
import type { FormEvent } from "react";

import { receiptFormKey, receiptRequest, receiptStart } from "../../inventory/forms";
import type { ReceiptFieldLine } from "../../inventory/forms";
import type { HoldRow, OrderCard } from "../../inventory/orderModel";
import type { InventoryCall } from "../../inventory/state";

export type OrdersHandlers = {
  onRefreshOrder: (orderId: string) => void;
  onReceive: (orderId: string, lines: { item_id: string; quantity: string; already_counted: boolean }[]) => void;
  onResolveHold: (holdId: string) => void;
  onReviewHold: (holdId: string) => void;
  onEdited: (form: "receipt") => void;
};

type Props = { orders: OrderCard[]; holds: HoldRow[]; saved: number; busy: InventoryCall | null; on: OrdersHandlers };

/** 입고 양식: 줄마다 입고 수량(남은 수량으로 시작)과 이미 마감에서 셌어요. 판단은 forms.ts의 receiptRequest. */
function ReceiptForm({ card, busy, onReceive, onEdited }: { card: OrderCard; busy: InventoryCall | null; onReceive: OrdersHandlers["onReceive"]; onEdited: () => void }) {
  const [lines, setLines] = useState<ReceiptFieldLine[]>(() => receiptStart(card));
  const request = receiptRequest(lines);
  const lineOf = (itemId: string) => card.lines.find((l) => l.itemId === itemId);
  const set = (itemId: string, patch: Partial<ReceiptFieldLine>) => {
    setLines((current) => current.map((l) => (l.itemId === itemId ? { ...l, ...patch } : l)));
    onEdited();
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && busy === null) onReceive(card.orderId, request.lines);
  };
  return (
    <form className="stack" onSubmit={submit}>
      <h4>입고 기록</h4>
      {lines.map((f) => {
        const line = lineOf(f.itemId);
        return (
          <div key={f.itemId} className="inv-order-line inv-wrap">
            <span className="inv-line-name">{line?.name}</span>
            <input inputMode="decimal" aria-label={`${line?.name} 입고 수량(${line?.unit})`} disabled={busy !== null} value={f.quantity} onChange={(e) => set(f.itemId, { quantity: e.target.value })} />
            <label className="row">
              <input type="checkbox" aria-label={`${line?.name} 이미 마감에서 셌어요`} disabled={busy !== null} checked={f.alreadyCounted} onChange={(e) => set(f.itemId, { alreadyCounted: e.target.checked })} />
              이미 마감에서 셌어요
            </label>
          </div>
        );
      })}
      <div className="row">
        <button type="submit" className="btn primary" disabled={busy !== null || request === null}>
          {busy === "save" ? "저장 중…" : "입고 저장"}
        </button>
      </div>
    </form>
  );
}

function HoldItem({ hold, busy, on }: { hold: HoldRow; busy: InventoryCall | null; on: OrdersHandlers }) {
  const orderId = hold.orderId;
  return (
    <li className="card stack">
      <div className="inv-line inv-wrap">
        <strong className="inv-line-name">{hold.itemName}</strong>
        <span>{hold.reasonLabel}</span>
        <span className="muted">{hold.createdDate}</span>
        {hold.priceText !== null && <span>{`새 단가 ${hold.priceText}`}</span>}
      </div>
      {hold.reordered && <p className="muted">새 단가로 다시 주문했어요. 확인했으면 해결로 표시해 주세요.</p>}
      <div className="row inv-wrap">
        {hold.canReview && (
          <button type="button" className="btn primary" disabled={busy !== null} onClick={() => on.onReviewHold(hold.holdId)}>
            새 단가로 다시 주문
          </button>
        )}
        {hold.canRefresh && orderId !== null && (
          <button type="button" className="btn" disabled={busy !== null} onClick={() => on.onRefreshOrder(orderId)}>
            {busy === "refresh" ? "확인 중…" : "다시 확인"}
          </button>
        )}
        <button type="button" className="btn" disabled={busy !== null} onClick={() => on.onResolveHold(hold.holdId)}>
          {busy === "resolve" ? "처리 중…" : "해결로 표시"}
        </button>
      </div>
    </li>
  );
}

function OrderItem({ card, saved, busy, on }: { card: OrderCard; saved: number; busy: InventoryCall | null; on: OrdersHandlers }) {
  return (
    <li className="card stack">
      <div className="row inv-wrap">
        <h3 className="grow">{card.supplierName}</h3>
        <span className="inv-badge">{card.originLabel}</span>
        <span className="inv-badge">{card.statusLabel}</span>
      </div>
      <p className="muted">{`${card.createdDate} · 총액 ${card.totalText}`}</p>
      <ul className="inv-lines">
        {card.lines.map((l) => (
          <li key={l.itemId} className="inv-line inv-wrap">
            <span className="inv-line-name">{l.name}</span>
            <span>{`주문 ${l.ordered}`}</span>
            <span>{`입고 ${l.received}`}</span>
            <span className="muted">{`남은 ${l.remaining}`}</span>
          </li>
        ))}
      </ul>
      {card.canRefresh && (
        <div className="row">
          <button type="button" className="btn" disabled={busy !== null} onClick={() => on.onRefreshOrder(card.orderId)}>
            {busy === "refresh" ? "확인 중…" : "다시 확인"}
          </button>
        </div>
      )}
      {card.canReceive && (
        <ReceiptForm
          key={receiptFormKey(saved, card)}
          card={card}
          busy={busy}
          onReceive={on.onReceive}
          onEdited={() => on.onEdited("receipt")}
        />
      )}
    </li>
  );
}

/** S10·S11 주문·입고 탭: 위에 보류, 아래에 주문 목록. */
export function OrdersScreen({ orders, holds, saved, busy, on }: Props) {
  return (
    <div className="stack">
      <section className="stack" aria-label="보류">
        <h2>보류</h2>
        {holds.length === 0 ? (
          <p className="muted">보류된 일이 없어요</p>
        ) : (
          <ul className="inv-list">
            {holds.map((h) => (
              <HoldItem key={h.holdId} hold={h} busy={busy} on={on} />
            ))}
          </ul>
        )}
      </section>
      <section className="stack" aria-label="주문">
        <h2>주문</h2>
        {orders.length === 0 ? (
          <p className="muted">주문이 없어요</p>
        ) : (
          <ul className="inv-list">
            {orders.map((o) => (
              <OrderItem key={o.orderId} card={o} saved={saved} busy={busy} on={on} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
