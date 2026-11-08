import type { ItemKind } from "../../api/types";
import type { AnomalyRow, CloseModel } from "../../inventory/screenModel";
import type { InventoryCall } from "../../inventory/state";
import { ItemFilter } from "./ItemFilter";
import type { FilterChange } from "./ItemFilter";

export type CloseHandlers = {
  onFilter: (filter: FilterChange) => void;
  onCount: (itemId: string, text: string) => void;
  onCheck: () => void;
  onConfirm: (itemId: string, confirmed: boolean) => void;
  onAdjust: (itemId: string, delta: string, reason: string) => void;
  onSave: (date: string) => void;
  onDate: (date: string) => void;
  onReset: () => void;
  onOpenStock: () => void;
};

type Props = {
  model: CloseModel;
  filter: { query: string; kind: ItemKind | "all" };
  busy: InventoryCall | null;
  on: CloseHandlers;
};

function AnomalyItem({ row, working, on }: { row: AnomalyRow; working: boolean; on: CloseHandlers }) {
  const needsReason = row.adjustment.delta.trim() !== "" && row.adjustment.reason.trim() === "";
  return (
    <li className="card stack8">
      <p>
        <strong>{row.name}</strong> · {row.kindLabel}
      </p>
      <p className="muted">{row.change}</p>
      <div className="row">
        <button
          type="button"
          className="btn compact"
          aria-pressed={row.confirmed}
          disabled={working || needsReason}
          onClick={() => on.onConfirm(row.itemId, !row.confirmed)}
        >
          {row.confirmed ? "확인했어요" : "맞아요"}
        </button>
        <label htmlFor={`adj-delta-${row.itemId}`} className="small">
          조정 수량(±)
        </label>
        <input
          id={`adj-delta-${row.itemId}`}
          inputMode="text"
          value={row.adjustment.delta}
          disabled={working}
          onChange={(event) => on.onAdjust(row.itemId, event.target.value, row.adjustment.reason)}
        />
        <label htmlFor={`adj-reason-${row.itemId}`} className="small">
          사유
        </label>
        <input
          id={`adj-reason-${row.itemId}`}
          value={row.adjustment.reason}
          disabled={working}
          onChange={(event) => on.onAdjust(row.itemId, row.adjustment.delta, event.target.value)}
        />
      </div>
      {needsReason && (
        <p className="small" role="alert">
          조정에는 사유가 꼭 필요해요.
        </p>
      )}
    </li>
  );
}

/** S05 하루 마감: 실사 입력 → 검사(이상 수량) → 마감 저장 → 결과. 요청 중엔 입력·버튼을 모두 막는다. */
export function CloseScreen({ model, filter, busy, on }: Props) {
  const working = busy !== null;
  if (model.result !== null) {
    return (
      <div className="card stack">
        <h2>마감을 저장했어요</h2>
        <p>{`저장한 날짜: ${model.result.savedDate}`}</p>
        <p>{model.result.summary}</p>
        {model.result.rows.length > 0 && (
          <ul>
            {model.result.rows.map((r) => (
              <li key={r.itemId}>
                {r.name}: {r.text}
              </li>
            ))}
          </ul>
        )}
        <div className="row">
          <button type="button" className="btn primary" onClick={on.onOpenStock}>
            재고 현황 보기
          </button>
          <button type="button" className="btn" onClick={on.onReset}>
            새 마감 시작
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className="stack">
      <div className="row">
        <label htmlFor="close-date">마감 날짜</label>
        <input id="close-date" type="date" value={model.date} disabled={working} onChange={(event) => on.onDate(event.target.value)} />
      </div>
      <p className="muted">비워 두면 미입력으로 남아요(0이 아니에요)</p>
      <ItemFilter idPrefix="close" query={filter.query} kind={filter.kind} disabled={working} onChange={on.onFilter} />
      {model.rows.length === 0 ? (
        <p className="muted">조건에 맞는 품목이 없어요.</p>
      ) : (
        <ul className="stack8">
          {model.rows.map((r) => (
            <li key={r.itemId} className="row">
              <span className="grow">
                {`${r.name}${r.option !== "" ? ` (${r.option})` : ""} · 지난 수량 ${r.previous}`}
              </span>
              <label htmlFor={`count-${r.itemId}`} className="small">
                {`${r.name} 실사 수량(${r.unit})`}
              </label>
              <input
                id={`count-${r.itemId}`}
                inputMode="decimal"
                value={r.input}
                placeholder="미입력"
                disabled={working}
                onChange={(event) => on.onCount(r.itemId, event.target.value)}
              />
            </li>
          ))}
        </ul>
      )}
      {model.anomalies.length > 0 && (
        <section className="stack8" aria-label="이상 수량 확인">
          <h2>수량을 다시 확인해 주세요</h2>
          <ul className="stack8">
            {model.anomalies.map((a) => (
              <AnomalyItem key={a.itemId} row={a} working={working} on={on} />
            ))}
          </ul>
        </section>
      )}
      <div className="row">
        <button type="button" className="btn" disabled={!model.canCheck || working} onClick={on.onCheck}>
          {busy === "check" ? "검사 중…" : "검사"}
        </button>
        <button type="button" className="btn primary" disabled={!model.canSave || working} onClick={() => on.onSave(model.date)}>
          {busy === "close" ? "저장 중…" : "마감 저장"}
        </button>
      </div>
    </div>
  );
}
