import type { SessionSummary } from "../api/types";
import { formatDate } from "../lib/format";
import { modeName } from "../lib/modes";
import { useFocusOnShrink } from "../lib/useFocusOnShrink";
import { stageLabel } from "../lib/sessions";
import { WorkItemActions } from "../components/WorkItemDialogs";
import { EmptyState } from "./EmptyState";

type Props = {
  sessions: SessionSummary[];
  busy: boolean;
  onResume: (summary: SessionSummary) => void;
  onRename: (sessionId: string, name: string) => void;
  onDelete: (sessionId: string) => void;
  onHome: () => void;
};

/** 내 작업: 세션마다 진행 단계와 이어서 작업하기. */
export function WorkScreen({ sessions, busy, onResume, onRename, onDelete, onHome }: Props) {
  const heading = useFocusOnShrink(sessions.length);
  return (
    <section className="list stack">
      <p className="small">MY WORK</p>
      <h1 ref={heading} tabIndex={-1} className="screen-title">내 작업</h1>
      <p className="muted">자동 저장된 단계부터 이어서 작업하세요.</p>
      {sessions.length === 0 ? (
        <EmptyState title="아직 시작한 작업이 없어요" body="과제를 고르고 요청을 보내면 여기에 모여요." onHome={onHome} />
      ) : (
        sessions.map((summary) => (
          <article key={summary.session_id} className="card listitem">
            <div className="grow stack8">
              <h2>{`${summary.name} · ${summary.title}`}</h2>
              <p className="muted">{`${modeName(summary.mode)} · ${stageLabel(summary)} · ${formatDate(summary.updated_at)}`}</p>
            </div>
            <div className="item-buttons">
              <button type="button" className="btn" onClick={() => onResume(summary)}>
                이어서 작업하기 →
              </button>
              <WorkItemActions
                summary={summary}
                busy={busy}
                onRename={(name) => onRename(summary.session_id, name)}
                onDelete={() => onDelete(summary.session_id)}
              />
            </div>
          </article>
        ))
      )}
      <p className="small muted">작업은 이 브라우저의 익명 사용자로 서버에 저장돼요. 문서를 내려받으면 따로 보관할 수 있어요.</p>
    </section>
  );
}
