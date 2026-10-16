import type { SummaryItem } from "../api/types";

export function SummaryList({ items }: { items: SummaryItem[] }) {
  return (
    <section className="card">
      <h3>지금까지 확인된 정보</h3>
      <ul>
        {items.map((item) => (
          <li key={item.field}>
            {item.label}: {item.value} <span className="badge">{item.source_label}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
