import { useState } from "react";

import type { AnswerBody, Question } from "../api/types";
import { questionHint } from "../lib/questionHint";
import { toggleSelection } from "../lib/selection";

type Props = {
  question: Question;
  busy: boolean;
  onAnswer: (body: AnswerBody) => void;
};

/** 질문이 바뀌면 부모가 key(question_id)로 새로 만들어 선택·입력 상태가 비워진다. */
export function QuestionCard({ question, busy, onAnswer }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");

  function toggle(id: string) {
    setSelected((prev) => toggleSelection(prev, id, question.multi_select));
  }

  const options = question.options;
  const hint = questionHint(question);

  return (
    <section className="card">
      {hint && <p className="hint">{hint}</p>}
      <h2>{question.text}</h2>
      {question.multi_select && <p className="hint">여러 개 고를 수 있어요</p>}

      {options.length > 0 && (
        <div className="chips">
          {options.map((o) => (
            <button
              key={o.id}
              type="button"
              className={selected.includes(o.id) ? "chip on" : "chip"}
              onClick={() => toggle(o.id)}
            >
              {o.label}
              {o.ai_suggested && <span className="badge">AI 제안</span>}
            </button>
          ))}
        </div>
      )}
      {selected.length > 0 && (
        <button
          type="button"
          disabled={busy}
          onClick={() => onAnswer({ answer_type: "option", option_ids: selected })}
        >
          선택 완료
        </button>
      )}

      <textarea
        value={text}
        placeholder="직접 입력"
        onChange={(e) => setText(e.target.value)}
        rows={2}
      />
      <button
        type="button"
        disabled={busy || !text.trim()}
        onClick={() => onAnswer({ answer_type: "free_text", value: text })}
      >
        직접 입력으로 답하기
      </button>

      <div className="row">
        <button type="button" className="ghost" disabled={busy} onClick={() => onAnswer({ answer_type: "easier" })}>
          다른 예시 보기
        </button>
        <button type="button" className="ghost" disabled={busy} onClick={() => onAnswer({ answer_type: "skip" })}>
          아직 모르겠어요
        </button>
      </div>
    </section>
  );
}
