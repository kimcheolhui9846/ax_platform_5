import type { ResultView, SessionView, TaskSummary, VersionSummary } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { ResultDocument } from "../components/ResultDocument";
import { SupplementPanel } from "../components/SupplementPanel";
import { STALE_NOTICE, actionState, regenerateAction, saveButton } from "../lib/actions";
import { documentContent } from "../lib/document";
import type { SupplementProps } from "./EditScreen";

type MainProps = {
  task: TaskSummary;
  session: SessionView;
  result: ResultView | null;
  busy: boolean;
  onConfirm: () => void;
};

/** 결과 문서. 아직 결과가 없으면 답변 확인으로 안내한다. */
export function ResultMain({ task, session, result, busy, onConfirm }: MainProps) {
  if (result === null) {
    return (
      <section className="card confirm stack">
        <h1>아직 만든 결과가 없어요</h1>
        <p className="muted">답변을 확인하고 초안을 만들어 주세요.</p>
        <button type="button" className="btn primary" disabled={busy} onClick={onConfirm}>
          답변 확인으로
        </button>
      </section>
    );
  }
  return <ResultDocument {...documentContent(task, result, session.result_stale)} />;
}

type SideProps = {
  session: SessionView;
  version: VersionSummary;
  busy: boolean;
  supplements: SupplementProps;
  onEditText: (() => void) | null;
  onRegenerate: () => void;
  onSave: () => void;
  onChangeAnswers: (() => void) | null;
  onContinue: () => void;
  onDownload: () => void;
};

/** 결과 화면 오른쪽: 흐름 요약과 다음 할 일(다시 만들기·저장·답변 바꾸기·이어 가기·내려받기). */
export function ResultSide({ session, version, busy, supplements, onEditText, onRegenerate, onSave, onChangeAnswers, onContinue, onDownload }: SideProps) {
  const regenerate = regenerateAction(session.result_stale);
  const regenerateState = actionState(regenerate, busy, session.can_generate);
  const save = saveButton(version, session.result_stale);
  return (
    <section className="card side-card stack" aria-label="결과 다음 할 일">
      <h2>결과를 확인해 주세요</h2>
      {session.result_stale && <p className="notice small">{STALE_NOTICE}</p>}
      {session.error && (
        <p className="error" role="alert">
          {session.error}
        </p>
      )}
      <FlowSummary flow={session.flow} />
      <SupplementPanel {...supplements} busy={busy} />
      <div className="stack8">
        <button
          type="button"
          className={regenerate.primary ? "btn primary full" : "btn full"}
          disabled={regenerateState.disabled}
          onClick={onRegenerate}
        >
          {regenerateState.label}
        </button>
        <button type="button" className={save.primary ? "btn primary full" : "btn full"} disabled={busy || save.done} onClick={onSave}>
          {save.label}
        </button>
        {onEditText && (
          <button type="button" className="btn full" disabled={busy} onClick={onEditText}>
            소개 문구 수정하기
          </button>
        )}
        {onChangeAnswers && (
          <button type="button" className="btn full" disabled={busy} onClick={onChangeAnswers}>
            기준 답변 바꾸기
          </button>
        )}
        <button type="button" className="btn full" disabled={busy} onClick={onContinue}>
          질문 이어 가기
        </button>
        <button type="button" className="btn full" disabled={busy} onClick={onDownload}>
          문서 내려받기
        </button>
      </div>
      <p className="small muted">AI 제안과 외부 사실은 따로 검토가 필요해요.</p>
    </section>
  );
}
