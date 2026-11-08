import { moneyText, quantityText } from "../../lib/inventory/format";
import type { InventoryCall } from "../../inventory/state";
import type { ProposalGroup } from "../../inventory/orderModel";

type Props = { groups: ProposalGroup[]; busy: InventoryCall | null; onOpen: (supplierId: string) => void };

/** S06 부족한 구매 품목: 거래처별 제안. 서버가 한 주문에 한 거래처만 받으므로 카드도 거래처별이다. */
export function OrderProposal({ groups, busy, onOpen }: Props) {
  if (groups.length === 0) return null;
  return (
    <section className="stack" aria-label="부족한 구매 품목">
      <h2>부족한 구매 품목</h2>
      {groups.map((g) => (
        <div key={g.supplierId} className="card stack">
          <div className="row inv-wrap">
            <h3 className="grow">{g.supplierName}</h3>
            <button type="button" className="btn primary" aria-label={`${g.supplierName} 주문 확인`} disabled={busy !== null} onClick={() => onOpen(g.supplierId)}>
              주문 확인
            </button>
          </div>
          <ul className="inv-lines">
            {g.lines.map((l) => (
              <li key={l.itemId} className="inv-line inv-wrap">
                <span className="inv-line-name">{l.name}</span>
                <span>{`제안 ${quantityText(l.suggested, l.unit)}`}</span>
                <span className="muted">{`단가 ${moneyText(l.unitPrice)}`}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
