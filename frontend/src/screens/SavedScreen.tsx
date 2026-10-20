import type { SessionView, TaskSummary, VersionView } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { versionLine } from "../lib/sessions";
import type { DocumentFormat } from "../lib/documentFormats";

type MainProps = {
  task: TaskSummary;
  version: VersionView;
  next: { title: string; onStart: () => void } | null;
  onDocuments: () => void;
  onOpen: () => void;
  onDownload: (format: DocumentFormat) => void;
};

/** 저장 완료. 저장한 그 버전을 결과물 목록·다시 보기·내려받기로 이어 준다. */
export function SavedMain({ task, version, next, onDocuments, onOpen, onDownload }: MainProps) {
  return (
    <section className="card saved stack">
      <p className="small">✓ 저장 완료</p>
      <h1>{`${task.title} 초안을 저장했어요.`}</h1>
      <p className="muted">{`결과물 목록에서 이 버전(${versionLine(version.version)})을 다시 열 수 있어요.`}</p>
      <div className="saved-actions">
        {next && (
          <button type="button" className="btn primary" onClick={next.onStart}>
            {`이 결과로 ${next.title} 시작`}
          </button>
        )}
        <button type="button" className={next ? "btn" : "btn primary"} onClick={onDocuments}>
          결과물 목록 보기
        </button>
        <button type="button" className="btn" onClick={onOpen}>
          저장한 결과 다시 보기
        </button>
      </div>
      <div className="saved-actions">
        <button type="button" className="btn" onClick={() => onDownload("html")}>
          문서 내려받기
        </button>
      </div>
      {next && <p className="small muted">다음 작업에는 현재 결과의 핵심 내용과 보완 정보를 전달해요. 가져온 내용은 제외할 수 있습니다.</p>}
    </section>
  );
}

export function SavedSide({ session }: { session: SessionView }) {
  return (
    <section className="card side-card stack" aria-label="저장한 결과의 기준">
      <FlowSummary flow={session.flow} />
      <p className="small muted">저장한 버전은 서버에 남아요. 내려받은 문서는 따로 공유할 수 있어요.</p>
    </section>
  );
}
