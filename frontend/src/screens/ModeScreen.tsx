import type { CoachingMode, TaskForm } from "../api/types";
import { MODE_COPY, RECOMMENDED_MODE } from "../lib/modes";

type Props = {
  form: TaskForm;
  draft: string;
  busy: boolean;
  onPick: (mode: CoachingMode) => void;
  onEditRequest: () => void;
};

/** 02 코칭 모드 선택. 모드를 고르는 순간 세션을 만든다(질문 상한은 모드마다 다르다). */
export function ModeScreen({ form, draft, busy, onPick, onEditRequest }: Props) {
  if (!draft.trim()) {
    return (
      <section className="mode-view stack">
        <h1>먼저 요청을 보내 주세요</h1>
        <p className="muted">코칭은 보낸 요청에서 시작해요.</p>
        <button type="button" className="btn primary" onClick={onEditRequest}>
          요청 쓰러 가기
        </button>
      </section>
    );
  }
  return (
    <section className="mode-view stack">
      <div className="stack12">
        <p className="small">02 / 코칭 모드 선택</p>
        <h1>어떤 방식으로 코칭받고 싶으세요?</h1>
        <p className="bodycopy muted">원하는 깊이에 맞춰 선택해 주세요. 보낸 요청을 바탕으로 코칭을 시작해요.</p>
      </div>
      <div className="card stack8">
        <p className="muted">내가 보낸 요청</p>
        <p className="bodycopy">{draft}</p>
      </div>
      <div className="mode-grid">
        {form.modes.map(({ mode }) => {
          const copy = MODE_COPY[mode];
          return (
            <article key={mode} className="card mode-card stack">
              <h2>{copy.name}</h2>
              <p className="bodycopy">{copy.headline}</p>
              <p className="muted">{copy.detail}</p>
              <button
                type="button"
                className={mode === RECOMMENDED_MODE ? "btn primary full" : "btn full"}
                disabled={busy}
                onClick={() => onPick(mode)}
              >
                {busy ? "코칭을 준비하는 중…" : `${copy.name} 코칭 시작`}
              </button>
            </article>
          );
        })}
      </div>
      <div className="row">
        <button type="button" className="btn" disabled={busy} onClick={onEditRequest}>
          ← 요청 수정하기
        </button>
        <span className="muted grow">중간에도 현재 정보로 초안을 만들 수 있어요.</span>
      </div>
    </section>
  );
}
