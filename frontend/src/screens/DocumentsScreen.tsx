import type { SessionSummary } from "../api/types";
import { formatDate } from "../lib/format";
import { savedDocuments, versionLine } from "../lib/sessions";
import { EmptyState } from "./EmptyState";

type Props = {
  sessions: SessionSummary[];
  busy: boolean;
  onOpen: (sessionId: string, version: number) => void;
  onUnsave: (sessionId: string, version: number) => void;
  onHome: () => void;
};

/** 결과물: 저장한 버전을 최근에 만든 순서로. */
export function DocumentsScreen({ sessions, busy, onOpen, onUnsave, onHome }: Props) {
  const documents = savedDocuments(sessions);
  return (
    <section className="list stack">
      <p className="small">MY DOCUMENTS</p>
      <h1 className="screen-title">결과물</h1>
      <p className="muted">저장한 버전을 골라 다시 확인하세요.</p>
      {documents.length === 0 ? (
        <EmptyState
          title="아직 저장한 결과가 없어요"
          body="코칭을 진행하고 결과에서 '현재 버전 저장'을 눌러 주세요."
          onHome={onHome}
        />
      ) : (
        documents.map(({ session, version }) => (
          <article key={`${session.session_id}-${version.version}`} className="card listitem">
            <div className="grow stack8">
              <h2>{session.name}</h2>
              <p className="muted">{`${session.title} 초안 · V${version.version}`}</p>
              <p className="small muted">{`${versionLine(version)} · ${formatDate(version.created_at)}`}</p>
            </div>
            <div className="item-buttons">
              <button type="button" className="btn" onClick={() => onOpen(session.session_id, version.version)}>
                이 버전 열기 →
              </button>
              <button type="button" className="btn compact" disabled={busy} onClick={() => onUnsave(session.session_id, version.version)}>
                결과물에서 빼기
              </button>
            </div>
          </article>
        ))
      )}
    </section>
  );
}
