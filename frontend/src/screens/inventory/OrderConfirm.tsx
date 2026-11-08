import type { InventoryCall } from "../../inventory/state";
import type { OrderConfirmModel } from "../../inventory/orderModel";

export type OrderConfirmHandlers = {
  onQuantity: (itemId: string, quantity: string) => void;
  onRemove: (itemId: string) => void;
  onCancel: () => void;
  onPlace: () => void;
  onOpenItems: () => void;
};

type Props = { model: OrderConfirmModel; busy: InventoryCall | null; on: OrderConfirmHandlers };

/** S07 주문 확인 카드(탭 줄 아래, 모든 탭에서 보인다). 수량·줄 빼기는 초안을 바꾸고, 보내는 건 주문하기뿐이다. */
export function OrderConfirm({ model, busy, on }: Props) {
  return (
    <section className="card stack" aria-label="주문 확인">
      <h2>{`주문 확인: ${model.supplierName}`}</h2>
      {model.repriced && <p className="notice">거래처가 알려 준 새 단가로 주문해요</p>}
      {model.lines.length === 0 && <p className="muted">주문할 품목이 없어요.</p>}
      {model.lines.map((l) => (
        <div key={l.itemId} className="inv-order-line inv-wrap">
          <span className="inv-line-name">{l.name}</span>
          <input
            inputMode="decimal"
            aria-label={`${l.name} 주문 수량(${l.unit})`}
            aria-invalid={l.valid ? undefined : true}
            disabled={busy !== null}
            value={l.quantity}
            onChange={(e) => on.onQuantity(l.itemId, e.target.value)}
          />
          <span className="muted">{`단가 ${l.unitPriceText}`}</span>
          <span>{`금액 ${l.amountText}`}</span>
          <button type="button" className="btn compact" disabled={busy !== null} onClick={() => on.onRemove(l.itemId)}>
            {`${l.name} 빼기`}
          </button>
        </div>
      ))}
      <p>{`예상 총액 ${model.totalText}(실제 금액은 주문 뒤 확인)`}</p>
      {model.addressMissing ? (
        <div className="notice stack" role="alert">
          <p>배송지를 먼저 설정해 주세요</p>
          <button type="button" className="btn" disabled={busy !== null} onClick={on.onOpenItems}>
            품목·기준으로 가기
          </button>
        </div>
      ) : (
        <p className="muted">{`배송지 ${model.address}`}</p>
      )}
      <div className="row inv-wrap">
        <button type="button" className="btn primary" disabled={!model.canSubmit || busy !== null} onClick={on.onPlace}>
          {busy === "order" ? "주문 중…" : "주문하기"}
        </button>
        <button type="button" className="btn" disabled={busy !== null} onClick={on.onCancel}>
          취소
        </button>
      </div>
    </section>
  );
}

/** 주문 응답 안내(접수·거절·접수 불명). */
export function OrderResultNotice({ text, onOpenOrders, onClose }: { text: string; onOpenOrders: () => void; onClose: () => void }) {
  return (
    <div className="notice stack" role="status">
      <p>{text}</p>
      <div className="row inv-wrap">
        <button type="button" className="btn" onClick={onOpenOrders}>
          주문·입고 보기
        </button>
        <button type="button" className="btn" onClick={onClose}>
          닫기
        </button>
      </div>
    </div>
  );
}
