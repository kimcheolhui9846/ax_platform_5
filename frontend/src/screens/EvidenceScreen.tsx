import type { EvidenceItem, FlowItem } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { proposalLabel, safeUrl } from "../lib/evidence";

/** 근거 자료 목록. 원문과 적용 범위를 보여 준다(제공 기관의 자료와 이 결과의 검증은 다르다). */
export function EvidenceMain({ items }: { items: EvidenceItem[] }) {
  return (
    <section className="card evidence stack" aria-label="근거 검토">
      <h1>근거 자료를 확인해 주세요</h1>
      <p className="muted">원문과 적용 범위를 살펴보고, 필요한 내용을 결과에 반영하세요.</p>
      {items.map((item) => {
        const url = safeUrl(item.url);
        return (
          <article key={item.id} className="card source-card stack8">
            <h2>{item.title}</h2>
            <p className="small muted">{`${item.publisher} · ${item.meta}`}</p>
            <p>{item.summary}</p>
            <p className="muted">{item.scope}</p>
            {url && (
              <a className="btn" href={url} target="_blank" rel="noopener noreferrer">
                원문 확인하기 ↗
              </a>
            )}
          </article>
        );
      })}
      <p className="small muted">결과에 수록하는 참고 자료예요. 제공 기관의 자료와 이 결과의 검증은 구분합니다.</p>
    </section>
  );
}

type SideProps = {
  flow: FlowItem[];
  items: EvidenceItem[];
  applied: Set<string>;
  busy: boolean;
  onApply: (sourceId: string) => void;
  onBack: () => void;
};

/** 결과에 반영할 점검 문구. 점검 문구가 있는 자료만 반영할 수 있고, 반영한 자료는 다시 누를 수 없다. */
export function EvidenceSide({ flow, items, applied, busy, onApply, onBack }: SideProps) {
  const proposals = items.filter((item) => item.record !== null);
  const anyApplied = proposals.some((item) => applied.has(item.id));
  return (
    <section className="card side-card stack" aria-label="반영할 내용">
      <h2>결과에 반영할 내용</h2>
      <FlowSummary flow={flow} />
      {proposals.map((item) => {
        const done = applied.has(item.id);
        return (
          <div key={item.id} className="notice stack8">
            <p className="label">{proposalLabel(item)}</p>
            <p>{item.record?.text}</p>
            {item.record?.caution && <p className="muted">{item.record.caution}</p>}
            <button type="button" className={done ? "btn full" : "btn primary full"} disabled={busy || done} onClick={() => onApply(item.id)}>
              {done ? "반영했어요" : `${item.record?.title} 반영`}
            </button>
          </div>
        );
      })}
      <button type="button" className="btn full" disabled={busy} onClick={onBack}>
        {anyApplied ? "검토 기록 유지하고 돌아가기" : "반영하지 않고 돌아가기"}
      </button>
    </section>
  );
}
