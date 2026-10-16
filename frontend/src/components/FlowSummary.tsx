import type { FlowItem } from "../api/types";

/** 결과 화면 오른쪽의 짧은 흐름 요약. 답했거나 미정으로 둔 질문만. */
export function FlowSummary({ flow }: { flow: FlowItem[] }) {
  const asked = flow.filter((item) => item.status === "answered" || item.status === "skipped");
  return (
    <section className="flow-compact" aria-label="질문 흐름 요약">
      <h3>질문 흐름 · 답한 질문</h3>
      {asked.length === 0 ? (
        <p className="small muted">아직 답한 질문이 없어요.</p>
      ) : (
        asked.map((item) => (
          <div key={item.field} className="summary-row">
            <span>{item.label}</span>
            <span>{item.answer ?? "아직 미정"}</span>
          </div>
        ))
      )}
    </section>
  );
}
