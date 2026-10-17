import type { TaskSummary, VersionView } from "../api/types";
import { ResultDocument } from "../components/ResultDocument";
import { documentContent } from "../lib/document";
import { formatDate } from "../lib/format";
import { versionLine, versionNotice } from "../lib/sessions";

type MainProps = { task: TaskSummary; version: VersionView; stale: boolean; onCurrent: () => void };

/** 버전 보기(보기 전용). 지난 버전이면 그렇다고 알리고 지금 버전으로 돌아가게 한다. stale은 versionIsStale로 정한다. */
export function VersionMain({ task, version, stale, onCurrent }: MainProps) {
  return (
    <div className="stack">
      <div className="notice version-notice">
        <p className="grow">
          {versionNotice(version.latest, stale)}
        </p>
        <button type="button" className="btn" onClick={onCurrent}>
          현재 버전으로
        </button>
      </div>
      <ResultDocument {...documentContent(task, version, stale, {})} />
    </div>
  );
}

type SideProps = { version: VersionView; onDocuments: () => void; onDownload: () => void };

export function VersionSide({ version, onDocuments, onDownload }: SideProps) {
  const summary = version.version;
  return (
    <section className="card side-card stack" aria-label="이 버전">
      <h2>이 버전</h2>
      <p>{`${versionLine(summary)} · ${formatDate(summary.created_at)}`}</p>
      {summary.saved && <p className="small muted">결과물에 저장한 버전이에요.</p>}
      <div className="stack8">
        <button type="button" className="btn full" onClick={onDownload}>
          문서 내려받기
        </button>
        <button type="button" className="btn full" onClick={onDocuments}>
          결과물 목록 보기
        </button>
      </div>
    </section>
  );
}
