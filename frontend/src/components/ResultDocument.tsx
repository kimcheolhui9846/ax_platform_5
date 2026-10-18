import { Fragment } from "react";

import { assumptionKey, formatAssumption } from "../lib/assumption";
import type { DocumentBlock, DocumentContent, DocumentRecord } from "../lib/document";
import { documentSections } from "../lib/document";
import { PRIVATE_LABEL } from "../lib/privacy";
import { CriteriaBox } from "./CriteriaBox";

function Blocks({ blocks }: { blocks: DocumentBlock[] }) {
  return (
    <>
      {blocks.map((block) =>
        block.kind === "text" ? (
          <p key={block.key}>{block.text}</p>
        ) : (
          <figure key={block.key} className="document-image">
            {block.src !== null ? (
              <div className="image-slot">
                <img src={block.src} alt={block.alt} />
              </div>
            ) : (
              <div className="image-slot" role="img" aria-label={block.alt}>
                <span className="image-symbol" aria-hidden="true">
                  ▧
                </span>
                <span className="small muted">이미지를 불러오는 중이거나 불러오지 못했어요</span>
              </div>
            )}
            <figcaption>
              <h3>{block.alt}</h3>
              {block.caption && <p>{block.caption}</p>}
            </figcaption>
          </figure>
        ),
      )}
    </>
  );
}

function EvidenceRecordBox({ record }: { record: DocumentRecord }) {
  return (
    <section className="evidence-record stack8" aria-label={record.label}>
      <p className="label">{record.label}</p>
      <p>{record.text}</p>
      <p className="small">
        {record.url ? (
          <a href={record.url} target="_blank" rel="noopener noreferrer">
            {`${record.source} ↗`}
          </a>
        ) : (
          record.source
        )}
        {record.note && ` · ${record.note}`}
      </p>
    </section>
  );
}

/** 결과 문서. 섹션은 순서대로 번호를 매기고(글·이미지 블록), 근거 기록은 그 섹션 뒤에, AI 가정과 검토할 부분은 따로 둔다. */
export function ResultDocument({ title, kicker, rows, result, issues, supplements, images, trailing }: DocumentContent) {
  const { assumptions } = result;
  return (
    <article className="card document stack">
      <div className="doc-title stack8">
        <p className="small muted">{kicker}</p>
        <h1>{title}</h1>
      </div>
      <CriteriaBox rows={rows} />
      {documentSections(result.sections, result.evidence, images).map((section) => (
        <Fragment key={section.key}>
          <section className="document-section">
            <h2 className="section-heading">
              <span className="section-number">{section.number}</span>
              <span>{section.heading}</span>
              <span className="section-tag">{section.tag}</span>
            </h2>
            <Blocks blocks={section.blocks} />
          </section>
          {section.records.map((record) => (
            <EvidenceRecordBox key={record.key} record={record} />
          ))}
        </Fragment>
      ))}
      {trailing.map((record) => (
        <EvidenceRecordBox key={record.key} record={record} />
      ))}
      {supplements.length > 0 && (
        <section className="document-section applied-info stack8">
          <p className="label">보완 정보 · 사용자 입력 / 검증 전</p>
          {supplements.map((row) => (
            <div key={row.label} className="summary-row">
              <span>{row.label}</span>
              <span>
                {row.value}
                {row.private && <span className="muted">{` · ${PRIVATE_LABEL}`}</span>}
              </span>
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
