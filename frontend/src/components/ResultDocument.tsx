import { assumptionKey, formatAssumption } from "../lib/assumption";
import type { DocumentContent } from "../lib/document";
import { documentSections } from "../lib/document";
import { CriteriaBox } from "./CriteriaBox";

/** 결과 문서(텍스트). 섹션은 순서대로 번호를 매기고, AI 가정과 검토할 부분을 따로 둔다. */
export function ResultDocument({ title, kicker, rows, result, issues, supplements, images }: DocumentContent) {
  const { assumptions } = result;
  return (
    <article className="card document stack">
      <div className="doc-title stack8">
        <p className="small muted">{kicker}</p>
        <h1>{title}</h1>
      </div>
      <CriteriaBox rows={rows} />
      {documentSections(result.sections, result.evidence, images).map((section) => (
        <section key={section.key} className="document-section">
          <h2 className="section-heading">
            <span className="section-number">{section.number}</span>
            <span>{section.heading}</span>
            <span className="section-tag">{section.tag}</span>
          </h2>
          {section.blocks.map((block) =>
            block.kind === "text" ? (
              <p key={block.key}>{block.text}</p>
            ) : block.src ? (
              <img key={block.key} src={block.src} alt={block.alt} />
            ) : (
              <p key={block.key} className="small muted">[이미지: {block.alt}]</p>
            ),
          )}
        </section>
      ))}
      {supplements.length > 0 && (
        <section className="document-section applied-info stack8">
          <p className="label">보완 정보 · 사용자 입력 / 검증 전</p>
          {supplements.map((row) => (
            <div key={row.label} className="summary-row">
              <span>{row.label}</span>
              <span>{row.value}</span>
            </div>
          ))}
        </section>
      )}
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
