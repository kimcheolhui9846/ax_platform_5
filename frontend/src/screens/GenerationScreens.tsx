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
