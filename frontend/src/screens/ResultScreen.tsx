import type { ResultView, SessionView, TaskSummary } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { ResultDocument } from "../components/ResultDocument";
import { STALE_NOTICE, actionState, regenerateAction } from "../lib/actions";
import { criteriaRows } from "../lib/criteria";
import { resultKicker, resultTitle } from "../lib/document";

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
  return (
    <ResultDocument
      result={result}
      title={resultTitle(task.title)}
      kicker={resultKicker(task.deliverable, session.result_stale)}
      rows={criteriaRows(session.summary, session.unknowns)}
    />
  );
}

type SideProps = {
  session: SessionView;
  busy: boolean;
  onRegenerate: () => void;
  onChangeAnswers: (() => void) | null;
  onContinue: () => void;
};

/** 결과 화면 오른쪽: 흐름 요약과 다음 할 일. */
export function ResultSide({ session, busy, onRegenerate, onChangeAnswers, onContinue }: SideProps) {
  const regenerate = regenerateAction(session.result_stale);
  const { label, disabled } = actionState(regenerate, busy, session.can_generate);
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
      <div className="stack8">
        <button type="button" className={regenerate.primary ? "btn primary full" : "btn full"} disabled={disabled} onClick={onRegenerate}>
          {label}
        </button>
        {onChangeAnswers && (
          <button type="button" className="btn full" disabled={busy} onClick={onChangeAnswers}>
            기준 답변 바꾸기
          </button>
        )}
        <button type="button" className="btn full" disabled={busy} onClick={onContinue}>
          질문 이어 가기
        </button>
      </div>
      <p className="small muted">AI 제안과 외부 사실은 따로 검토가 필요해요.</p>
    </section>
  );
}
