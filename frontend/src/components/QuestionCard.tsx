import { useState } from "react";

import type { AnswerBody, Question } from "../api/types";
import { exampleActions, questionHint } from "../lib/question";
import type { ExampleAction } from "../lib/question";
import { Composer } from "./Composer";
import { OptionList } from "./OptionList";
import { PrivacyToggle } from "./PrivacyToggle";

type Props = {
  question: Question;
  kicker: string;
  request: string;
  defaultPrivate: boolean; // 이 질문의 항목이 지금 AI에 보내지 않음으로 정해져 있는지
  busy: boolean;
  onAnswer: (body: AnswerBody) => void;
  onExample: (action: ExampleAction["action"], isPrivate: boolean) => void; // '다른 예시 보기'도 비공개 체크를 싣는다
  onEarlyDraft: () => void;
};

/** 질문 하나. 비공개 체크는 이 답에 실려 간다(기본은 정책·이전 설정). 질문이 바뀌면 부모가 key(question_id)로 새로 만들어 고른 답·입력이 비워진다. */
export function QuestionCard({ question, kicker, request, defaultPrivate, busy, onAnswer, onExample, onEarlyDraft }: Props) {
  const [text, setText] = useState("");
  const [hidden, setHidden] = useState(defaultPrivate);
  return (
    <section className="card question-card stack">
      <div className="notice stack8">
        <p className="small muted">내가 보낸 요청</p>
        <p>{request}</p>
      </div>
      <p className="small">{`◈ AI 코치 · ${kicker}`}</p>
      <h1>{question.text}</h1>
      <p className="muted">{questionHint(question)}</p>
      <PrivacyToggle label="🔒 이 답은 AI에 보내지 않기" checked={hidden} disabled={busy} onChange={setHidden} />
      <OptionList question={question} busy={busy} onChoose={(ids) => onAnswer({ answer_type: "option", option_ids: ids, private: hidden })} />
      <div className="help-row">
        {exampleActions(question).map(({ action, label }) => (
          <button key={action} type="button" className="btn" disabled={busy} onClick={() => onExample(action, hidden)}>
            {label}
          </button>
        ))}
        <button type="button" className="btn" disabled={busy} onClick={() => onAnswer({ answer_type: "skip" })}>
          아직 모르겠어요
        </button>
        <button type="button" className="btn" disabled={busy} onClick={onEarlyDraft}>
          현재 정보로 초안 만들기
        </button>
      </div>
      <Composer
        label="직접 답변 · 의견"
        value={text}
        placeholder="내 생각을 적어 주세요"
        rows={2}
        maxLength={1200}
        submitLabel="전송 ↑"
        busy={busy}
        onChange={setText}
        onSubmit={(value) => onAnswer({ answer_type: "free_text", value, private: hidden })}
      />
    </section>
  );
}
