import type { ResultView, SessionView, TaskSummary } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { versionLine } from "../lib/sessions";

type MainProps = {
  task: TaskSummary;
  result: ResultView;
  onDocuments: () => void;
  onResult: () => void;
  onDownload: () => void;
};

/** 저장 완료. 결과물 목록과 다시 보기, 내려받기로 이어 준다. */
export function SavedMain({ task, result, onDocuments, onResult, onDownload }: MainProps) {
  return (
    <section className="card saved stack">
      <p className="small">✓ 저장 완료</p>
      <h1>{`${task.title} 초안을 저장했어요.`}</h1>
      <p className="muted">{`결과물 목록에서 이 버전(${versionLine(result.version)})을 다시 열 수 있어요.`}</p>
      <div className="saved-actions">
        <button type="button" className="btn primary" onClick={onDocuments}>
          결과물 목록 보기
        </button>
        <button type="button" className="btn" onClick={onResult}>
          저장한 결과 다시 보기
        </button>
      </div>
      <div className="saved-actions">
        <button type="button" className="btn" onClick={onDownload}>
          문서 내려받기
        </button>
      </div>
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
