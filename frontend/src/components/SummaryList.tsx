import type { SummaryItem } from "../api/types";
import { sourceLabel } from "../lib/labels";

export function SummaryList({ items }: { items: SummaryItem[] }) {
  return (
    <section className="card">
      <h3>지금까지 확인된 정보</h3>
      <ul>
        {items.map((item) => (
          <li key={item.field}>
            {item.label}: {item.value} <span className="badge">{sourceLabel(item.source)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
