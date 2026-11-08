import type { ReactNode } from "react";

export type DataColumn<Row> = {
  key: string;
  header: string;
  cell: (row: Row) => ReactNode;
  align?: "start" | "end";
};

type Props<Row> = {
  caption: string;
  columns: DataColumn<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  empty: string;
};

// 넓으면 표, 좁으면 같은 마크업을 CSS가 카드 목록으로 바꾼다(셀 앞에 data-label 머리글).
export function DataTable<Row>({ caption, columns, rows, rowKey, empty }: Props<Row>) {
  if (rows.length === 0) return <p className="data-table-empty">{empty}</p>;
  return (
    <table className="data-table">
      <caption>{caption}</caption>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key} scope="col" className={c.align === "end" ? "num" : undefined}>
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={rowKey(row)}>
            {columns.map((c) => (
              <td key={c.key} data-label={c.header} className={c.align === "end" ? "num" : undefined}>
                {c.cell(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
