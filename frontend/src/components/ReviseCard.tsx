import { useState } from "react";

import type { ReviseBody } from "../api/types";
import type { EditableFlowItem } from "../lib/flowView";
import { Composer } from "./Composer";
import { OptionList } from "./OptionList";

type Props = {
  item: EditableFlowItem;
  busy: boolean;
  onRevise: (body: ReviseBody) => void;
  onCancel: () => void;
};

/** 답했거나 미정으로 둔 질문의 답을 고친다. 부모가 key(question_id)로 새로 만든다. */
export function ReviseCard({ item, busy, onRevise, onCancel }: Props) {
  const [text, setText] = useState(item.answer ?? "");
  const { question } = item;
  const note =
    item.status === "skipped"
      ? "아직 미정으로 남겨 둔 질문이에요. 지금 답할 수 있으면 골라 주세요."
      : `지금 답: ${item.answer ?? ""}`;
  return (
    <section className="card question-card stack" aria-label="답변 고치기">
      <p className="small">{`◈ 답변 고치기 · ${item.label}`}</p>
      <h1>{question.text}</h1>
      <p className="muted">{note}</p>
      <OptionList question={question} busy={busy} onChoose={(ids) => onRevise({ answer_type: "option", option_ids: ids })} />
      <Composer
        label="직접 고쳐 쓰기"
        value={text}
        placeholder="고친 답을 적어 주세요"
        rows={2}
        maxLength={1200}
        submitLabel="고친 답 보내기"
        busy={busy}
        onChange={setText}
        onSubmit={(value) => onRevise({ answer_type: "free_text", value })}
      />
      <button type="button" className="btn" disabled={busy} onClick={onCancel}>
        고치지 않고 돌아가기
      </button>
    </section>
  );
}
