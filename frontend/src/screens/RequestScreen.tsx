import type { SessionContext, TaskForm, TaskSummary } from "../api/types";
import { Composer } from "../components/Composer";
import { ContextBox } from "../components/ContextBox";
import { CarryFailedNotice } from "../components/CarryFailedNotice";
import { PrivacyToggle } from "../components/PrivacyToggle";
import { NOTICE_TEXT } from "../lib/privacy";

type Props = {
  task: TaskSummary;
  form: TaskForm;
  draft: string;
  context: SessionContext | null;
  carryFailed: boolean;
  acknowledged: boolean; // 외부 전송 안내를 확인했는지
  busy: boolean;
  onAcknowledge: (acknowledged: boolean) => void;
  onExcludeContext: () => void;
  onChange: (text: string) => void;
  onSubmit: () => void;
};

/** 01 내 요청: 하고 싶은 이야기를 보낸다. 글은 초안으로 남고, 세션은 다음 화면에서 모드를 고를 때 만든다. */
export function RequestScreen({ task, form, draft, context, carryFailed, acknowledged, busy, onAcknowledge, onExcludeContext, onChange, onSubmit }: Props) {
  const example = form.input_examples[0] ?? null;
  return (
    <section className="request stack">
      <p className="small">01 / 내 요청</p>
      <h1>{`${task.title}에서 어떤 도움이 필요한가요?`}</h1>
      <p className="muted">질문이나 아이디어를 보내 주세요. 다음 단계에서 원하는 코칭 방식을 선택해요.</p>
      {carryFailed && <CarryFailedNotice busy={busy} onContinue={onExcludeContext} />}
      {context && <ContextBox context={context} busy={busy} onExclude={onExcludeContext} />}
      <div className="notice stack8">
        <p className="label">외부 AI 전송 안내</p>
        <p>{NOTICE_TEXT}</p>
        <PrivacyToggle label="확인했어요" checked={acknowledged} onChange={onAcknowledge} />
      </div>
      <Composer
        label="내 질문 · 의견"
        value={draft}
        placeholder={form.input_placeholder}
        rows={3}
        maxLength={2000}
        submitLabel="요청 전송 ↑"
        busy={false}
        canSubmit={acknowledged}
        onChange={onChange}
        onSubmit={() => onSubmit()}
      />
      {example && (
        <div className="notice stack12">
          <p className="label">막막하다면 이렇게 시작해 보세요</p>
          <p>{example}</p>
          <button type="button" className="btn" onClick={() => onChange(example)}>
            이 문장 넣기
          </button>
        </div>
      )}
    </section>
  );
}
