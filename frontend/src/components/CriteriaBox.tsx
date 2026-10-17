import type { CriteriaRow } from "../lib/criteria";

/** 내 답변에서 반영한 기준. 답변 확인과 결과 문서가 같이 쓴다. */
export function CriteriaBox({ rows }: { rows: CriteriaRow[] }) {
  return (
    <div className="notice criteria stack8">
      <p className="small muted">내 답변에서 반영한 기준</p>
      {rows.map((row) => (
        <div key={row.field} className="summary-row">
          <span>{row.label}</span>
          <span>
            {row.value}
            {row.note && <span className="muted">{` · ${row.note}`}</span>}
          </span>
        </div>
      ))}
    </div>
  );
}
