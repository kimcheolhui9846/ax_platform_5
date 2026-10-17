import type { FlowItem } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";

/** 초안 생성 중. 서버가 끝까지 처리하는 요청이라 취소 버튼은 두지 않는다. */
export function GeneratingMain() {
  return (
    <section className="card generation-card stack" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <p className="small">초안 생성 중</p>
      <h1>답변을 바탕으로 초안을 정리하고 있어요</h1>
      <p className="muted" role="status">
        선택한 기준과 보완 정보를 확인하고 있어요. 잠시만 기다려 주세요.
      </p>
      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="small muted">입력 내용과 이전 결과는 그대로 유지돼요.</p>
    </section>
  );
}

export function GeneratingSide({ flow }: { flow: FlowItem[] }) {
  return (
    <section className="card side-card stack" aria-label="정리할 기준">
      <h2>정리할 기준</h2>
      <FlowSummary flow={flow} />
    </section>
  );
}

type FailedProps = {
  hasResult: boolean;
  busy: boolean;
  canGenerate: boolean;
  onRetry: () => void;
  onConfirm: () => void;
  onShowResult: () => void;
};

/** 초안 생성 실패. 구체 사유는 알림으로 나가고, 여기서는 입력이 남아 있음을 알리고 다시 시도하게 한다. */
export function FailedMain({ hasResult, busy, canGenerate, onRetry, onConfirm, onShowResult }: FailedProps) {
  return (
    <section className="card generation-card stack">
      <p className="small">초안 생성 실패</p>
      <h1>초안을 만들지 못했어요</h1>
      <p className="muted" role="alert">
        생성을 완료하지 못했어요. 입력한 내용은 유지되어 있으니 다시 시도해 주세요.
      </p>
      <div className="state-actions">
        <button type="button" className="btn primary" disabled={busy || !canGenerate} onClick={onRetry}>
          다시 시도하기
        </button>
        <button type="button" className="btn" disabled={busy} onClick={onConfirm}>
          입력 내용 확인
        </button>
        {hasResult && (
          <button type="button" className="btn" disabled={busy} onClick={onShowResult}>
            이전 결과 보기
          </button>
        )}
      </div>
      <p className="small muted">입력 내용과 저장한 결과는 삭제되지 않았어요.</p>
    </section>
  );
}

export function FailedSide({ flow }: { flow: FlowItem[] }) {
  return (
    <section className="card side-card stack" aria-label="유지된 답변">
      <h2>유지된 답변</h2>
      <FlowSummary flow={flow} />
    </section>
  );
}
