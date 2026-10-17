import type { SessionView, TaskSummary } from "../api/types";
import { CriteriaBox } from "../components/CriteriaBox";
import { STALE_NOTICE, actionState, confirmActions } from "../lib/actions";
import type { ResultAction } from "../lib/actions";
import { criteriaRows } from "../lib/criteria";

type Props = {
  task: TaskSummary;
  session: SessionView;
  busy: boolean;
  onAct: (action: ResultAction["action"]) => void;
  onChangeAnswers: (() => void) | null;
  onBackToQuestion: (() => void) | null;
};

/** 03 답변 의미 확인: 이해한 기준을 보여 주고 초안을 만든다(최신 결과가 있으면 보기가 먼저). */
export function ConfirmScreen({ task, session, busy, onAct, onChangeAnswers, onBackToQuestion }: Props) {
  return (
    <section className="card confirm stack">
      <p className="small">03 / 답변 의미 확인</p>
      <h1>이렇게 이해했어요. 맞나요?</h1>
      <CriteriaBox rows={criteriaRows(session.summary, session.unknowns)} />
      {session.error && (
        <p className="error" role="alert">
          {session.error}
        </p>
      )}
      {session.result_stale && <p className="notice">{STALE_NOTICE}</p>}
      <p className="bodycopy">{`선택한 기준을 토대로 ${task.title} 초안을 정리할게요.`}</p>
      <p className="muted">아직 정하지 않은 내용은 미정으로 남기고, AI의 제안과 사용자 입력을 구분해요.</p>
      <div className="notice stack8">
        <p className="small muted">이번에 만들 결과</p>
        <h2>{task.deliverable}</h2>
      </div>
      {confirmActions(session).map((action) => {
        const { label, disabled } = actionState(action, busy, session.can_generate);
        return (
          <button
            key={action.action}
            type="button"
            className={action.primary ? "btn primary full" : "btn full"}
            disabled={disabled}
            onClick={() => onAct(action.action)}
          >
            {label}
          </button>
        );
      })}
      {onBackToQuestion && (
        <button type="button" className="btn full" disabled={busy} onClick={onBackToQuestion}>
          남은 질문에 마저 답하기
        </button>
      )}
      {onChangeAnswers && (
        <button type="button" className="btn full" disabled={busy} onClick={onChangeAnswers}>
          답변 바꿀게요
        </button>
      )}
    </section>
  );
}
