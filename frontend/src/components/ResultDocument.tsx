import type { ResultView } from "../api/types";
import { assumptionKey, formatAssumption } from "../lib/assumption";
import type { CriteriaRow } from "../lib/criteria";
import { documentSections } from "../lib/document";
import { CriteriaBox } from "./CriteriaBox";

type Props = { result: ResultView; title: string; kicker: string; rows: CriteriaRow[] };

/** 결과 문서(텍스트). 섹션은 순서대로 번호를 매기고, AI 가정과 검토할 부분을 따로 둔다. */
export function ResultDocument({ result, title, kicker, rows }: Props) {
  const { assumptions } = result.result;
  const issues = result.validation?.issues ?? [];
  return (
    <article className="card document stack">
      <div className="doc-title stack8">
        <p className="small muted">{kicker}</p>
        <h1>{title}</h1>
      </div>
      <CriteriaBox rows={rows} />
      {documentSections(result.result.cards).map((section) => (
        <section key={section.key} className="document-section">
          <h2 className="section-heading">
            <span className="section-number">{section.number}</span>
            <span>{section.heading}</span>
            <span className="section-tag">{section.tag}</span>
          </h2>
          <p>{section.body}</p>
        </section>
      ))}
      {assumptions.length > 0 && (
        <section className="document-section">
          <h2 className="section-heading">AI가 가정한 내용</h2>
          <ul>
            {assumptions.map((assumption, index) => (
              <li key={assumptionKey(assumption, index)}>{formatAssumption(assumption)}</li>
            ))}
          </ul>
        </section>
      )}
      {issues.length > 0 && (
        <section className="document-section review-needed">
          <h2 className="section-heading">검토가 필요한 부분</h2>
          <ul>
            {issues.map((issue, index) => (
              <li key={`${issue.rule}-${index}`}>{issue.message}</li>
            ))}
          </ul>
        </section>
      )}
    </article>
  );
}
