import type { ResultView } from "../api/types";
import { cardLabel } from "../lib/labels";

export function ResultPanel({ view }: { view: ResultView }) {
  const { result, validation } = view;
  const cards = [...result.cards].sort((a, b) => a.order - b.order);
  const assumptions = result.assumptions ?? [];
  const issues = validation?.issues ?? [];

  return (
    <section>
      {cards.map((card) => (
        <article key={`${card.card_type}-${card.order}`} className="card">
          <p className="hint">{cardLabel(card.card_type)}</p>
          <h3>{card.title}</h3>
          <p>{card.body}</p>
        </article>
      ))}

      {assumptions.length > 0 && (
        <article className="card">
          <h3>AI가 가정한 내용</h3>
          <ul>
            {assumptions.map((a) => (
              <li key={a.field}>
                {a.field}: {a.value}
                {a.requires_confirmation && " (확인 필요)"}
              </li>
            ))}
          </ul>
        </article>
      )}

      {issues.length > 0 && (
        <article className="card warn">
          <h3>검토가 필요한 부분</h3>
          <ul>
            {issues.map((i, idx) => (
              <li key={`${i.rule}-${idx}`}>{i.message}</li>
            ))}
          </ul>
        </article>
      )}

      <article className="card">
        <h3>완성본</h3>
        <pre className="full-text">{result.full_text}</pre>
        <button type="button" onClick={() => void navigator.clipboard.writeText(result.full_text)}>
          복사
        </button>
      </article>
    </section>
  );
}
