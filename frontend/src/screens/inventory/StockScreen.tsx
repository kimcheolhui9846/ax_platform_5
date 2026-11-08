import type { ItemKind } from "../../api/types";
import { DataTable } from "../../components/DataTable";
import type { DataColumn } from "../../components/DataTable";
import type { StockModel, StockRow } from "../../inventory/screenModel";
import { KIND_LABELS } from "../../lib/inventory/format";
import { ItemFilter } from "./ItemFilter";
import type { FilterChange } from "./ItemFilter";

type Props = {
  model: StockModel;
  /** 숨기지 않은 품목이 하나라도 있나(검색에 걸러진 것과 구별). */
  hasItems: boolean;
  filter: { query: string; kind: ItemKind | "all" };
  onFilter: (filter: FilterChange) => void;
  onStartClose: () => void;
  onOpenItems: () => void;
};

function badgeClass(status: StockRow["status"]): string {
  if (status === "short") return "inv-badge low";
  return status === "ok" ? "inv-badge ok" : "inv-badge";
}

const COLUMNS: DataColumn<StockRow>[] = [
  { key: "name", header: "품목", cell: (r) => r.name },
  { key: "option", header: "옵션", cell: (r) => r.option || "-" },
  { key: "kind", header: "종류", cell: (r) => KIND_LABELS[r.kind] },
  { key: "onHand", header: "보유", cell: (r) => r.onHand, align: "end" },
  { key: "inTransit", header: "배송 중", cell: (r) => r.inTransit, align: "end" },
  { key: "status", header: "상태", cell: (r) => <span className={badgeClass(r.status)}>{r.statusLabel}</span> },
  { key: "suggested", header: "제안 주문량", cell: (r) => r.suggested || "-", align: "end" },
];

/** S04 재고 현황. */
export function StockScreen({ model, hasItems, filter, onFilter, onStartClose, onOpenItems }: Props) {
  if (!hasItems) {
    return (
      <div className="card empty stack">
        <h2>등록한 품목이 없어요</h2>
        <p className="muted">먼저 품목을 등록하면 재고 현황과 하루 마감을 쓸 수 있어요.</p>
        <button type="button" className="btn primary" onClick={onOpenItems}>
          품목·기준으로 가기
        </button>
      </div>
    );
  }
  return (
    <div className="stack">
      <div className="row">
        <p className="grow">
          {`부족 ${model.shortCount}개 · 미입력 ${model.uncountedCount}개 · 마지막 마감 ${model.lastClose ?? "아직 없음"}`}
        </p>
        <button type="button" className="btn primary" onClick={onStartClose}>
          하루 마감 하기
        </button>
      </div>
      <ItemFilter query={filter.query} kind={filter.kind} onChange={onFilter} />
      <DataTable caption="재고 현황" columns={COLUMNS} rows={model.rows} rowKey={(r) => r.itemId} empty="조건에 맞는 품목이 없어요." />
    </div>
  );
}
