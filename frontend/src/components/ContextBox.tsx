import type { SessionContext } from "../api/types";
import { PRIVATE_LABEL } from "../lib/privacy";

type Props = { context: SessionContext; busy: boolean; onExclude: () => void };

/** 이전 작업에서 가져온 기준(다음 과제로 이어가기). 빼면 이 과제는 처음부터 묻는다. 이전 작업에서 비공개였던 항목은 표시를 붙인다. */
export function ContextBox({ context, busy, onExclude }: Props) {
  const items = context.items
    .map((item) => `${item.label}: ${item.value}${item.private ? ` (${PRIVATE_LABEL})` : ""}`)
    .join(" · ");
  return (
    <section className="notice stack8" aria-label="이전 작업에서 가져온 기준">
      <div className="row">
        <p className="label grow">이전 작업에서 가져온 기준</p>
        <button type="button" className="btn compact" disabled={busy} onClick={onExclude}>
          가져온 내용 제외
        </button>
      </div>
      <p>{context.title}</p>
      {context.summary && <p className="small muted">{context.summary}</p>}
      {items && <p className="small muted">{items}</p>}
    </section>
  );
}
