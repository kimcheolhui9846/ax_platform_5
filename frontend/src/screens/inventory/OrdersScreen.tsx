import { useState } from "react";
import type { FormEvent } from "react";

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

const POSITIVE = /^\d+(\.\d+)?$/;
const isPositive = (text: string) => POSITIVE.test(text) && Number(text) > 0;

/** 입고 양식: 줄마다 입고 수량(남은 수량으로 시작)과 이미 마감에서 셌어요. 빈 칸 줄은 보내지 않는다. */
function ReceiptForm({ card, busy, onReceive, onEdited }: { card: OrderCard; busy: InventoryCall | null; onReceive: OrdersHandlers["onReceive"]; onEdited: () => void }) {
  const open = card.lines.filter((l) => Number(l.remainingRaw) > 0);
  const [quantities, setQuantities] = useState<Record<string, string>>(() => Object.fromEntries(open.map((l) => [l.itemId, l.remainingRaw])));
  const [counted, setCounted] = useState<Record<string, boolean>>({});
  const filled = open.filter((l) => (quantities[l.itemId] ?? "").trim() !== "");
  const valid = filled.length > 0 && filled.every((l) => isPositive((quantities[l.itemId] ?? "").trim()));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!valid || busy !== null) return;
    onReceive(
      card.orderId,
      filled.map((l) => ({ item_id: l.itemId, quantity: (quantities[l.itemId] ?? "").trim(), already_counted: counted[l.itemId] === true })),
    );
  };
  return (
    <form className="stack" onSubmit={submit}>
      <h4>입고 기록</h4>
      {open.map((l) => (
        <div key={l.itemId} className="inv-order-line inv-wrap">
          <span className="inv-line-name">{l.name}</span>
          <input
            inputMode="decimal"
            aria-label={`${l.name} 입고 수량(${l.unit})`}
            disabled={busy !== null}
            value={quantities[l.itemId] ?? ""}
            onChange={(e) => {
              setQuantities((c) => ({ ...c, [l.itemId]: e.target.value }));
              onEdited();
            }}
          />
          <label className="row">
            <input
              type="checkbox"
              disabled={busy !== null}
              checked={counted[l.itemId] === true}
              onChange={(e) => {
                setCounted((c) => ({ ...c, [l.itemId]: e.target.checked }));
                onEdited();
              }}
            />
            이미 마감에서 셌어요
          </label>
        </div>
      ))}
      <div className="row">
        <button type="submit" className="btn primary" disabled={busy !== null || !valid}>
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
          key={`${saved}:${card.orderId}:${card.lines.map((l) => l.received).join(",")}`}
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
