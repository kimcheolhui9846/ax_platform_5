import { useState } from "react";

import type { Question } from "../api/types";
import { toggleSelection } from "../lib/selection";

type Props = {
  question: Pick<Question, "options" | "multi_select">;
  busy: boolean;
  onChoose: (optionIds: string[]) => void;
};

/** 선택지. 하나만 고르는 질문은 누르는 즉시 보내고, 여러 개 고르는 질문은 고른 뒤 한 번에 보낸다. */
export function OptionList({ question, busy, onChoose }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  if (question.options.length === 0) return null;
  const multi = question.multi_select;
  return (
    <>
      <div className="options" role="group" aria-label={multi ? "답 고르기 · 여러 개 고를 수 있어요" : "답 고르기"}>
        {question.options.map((option) => (
          <button
            key={option.id}
            type="button"
            className="btn full choice"
            aria-pressed={multi ? selected.includes(option.id) : undefined}
            disabled={busy}
            onClick={() => (multi ? setSelected((prev) => toggleSelection(prev, option.id, true)) : onChoose([option.id]))}
          >
            {option.label}
            {option.ai_suggested && <span className="badge">AI 제안</span>}
          </button>
        ))}
      </div>
      {multi && (
        <button type="button" className="btn primary" disabled={busy || selected.length === 0} onClick={() => onChoose(selected)}>
          고른 답 보내기
        </button>
      )}
    </>
  );
}
