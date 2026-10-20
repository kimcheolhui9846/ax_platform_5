import { useId } from "react";
import type { ResultView, SessionView, TaskSummary, VersionSummary } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";
import { ResultDocument } from "../components/ResultDocument";
import { SupplementPanel } from "../components/SupplementPanel";
import { STALE_BANNER, STALE_SAVE_HINT, REGENERATE_ACTION, actionState, saveButton } from "../lib/actions";
import { documentContent } from "../lib/document";
import type { Images } from "../lib/document";
import type { SupplementProps } from "./EditScreen";
import type { DocumentFormat } from "../lib/documentFormats";

type MainProps = {
  task: TaskSummary;
  session: SessionView;
  result: ResultView | null;
  images: Images;
  busy: boolean;
  onConfirm: () => void;
  onRegenerate: () => void;
};

type BannerProps = { busy: boolean; canGenerate: boolean; onRegenerate: () => void };

/** 결과가 최신이 아님(답·보완 정보가 바뀜). 아래 문서는 바뀌기 전 결과다. */
export function StaleBanner({ busy, canGenerate, onRegenerate }: BannerProps) {
  return (
    <section className="stale-banner" role="status">
      <div className="stack8">
        <h2>{STALE_BANNER.title}</h2>
        <p>{STALE_BANNER.text}</p>
      </div>
      <button type="button" className="btn primary" disabled={busy || !canGenerate} onClick={onRegenerate}>
        {STALE_BANNER.action}
      </button>
    </section>
  );
}

/** 결과 문서. 아직 결과가 없으면 답변 확인으로 안내한다. */
export function ResultMain({ task, session, result, images, busy, onConfirm, onRegenerate }: MainProps) {
  if (result === null) {
    return (
      <section className="card confirm stack">
        <h1>아직 만든 결과가 없어요</h1>
        <p className="muted">답변을 확인하고 초안을 만들어 주세요.</p>
        <button type="button" className="btn primary" disabled={busy} onClick={onConfirm}>
          답변 확인으로
        </button>
      </section>
    );
  }
  const document = <ResultDocument {...documentContent(task, result, session.result_stale, images)} />;
  if (!session.result_stale) return document;
  return (
    <div className="stack">
      <StaleBanner busy={busy} canGenerate={session.can_generate} onRegenerate={onRegenerate} />
      {document}
    </div>
  );
}

type SideProps = {
  session: SessionView;
  version: VersionSummary;
  heading: string;
  withSources: boolean;
  evidence: { label: string; primary: boolean; onReview: () => void } | null;
  onBeforeEvidence: (() => void) | null;
  busy: boolean;
  supplements: SupplementProps;
  onEditText: (() => void) | null;
  onRegenerate: () => void;
  onSave: () => void;
  onChangeAnswers: (() => void) | null;
  onContinue: () => void;
  onDownload: (format: DocumentFormat) => void;
};

/** 결과 화면 오른쪽: 흐름 요약과 다음 할 일(다시 만들기·저장·답변 바꾸기·이어 가기·내려받기). */
export function ResultSide({
  session,
  version,
  heading,
  withSources,
  evidence,
  onBeforeEvidence,
  busy,
  supplements,
  onEditText,
  onRegenerate,
  onSave,
  onChangeAnswers,
  onContinue,
  onDownload,
}: SideProps) {
  const hintId = useId();
  const stale = session.result_stale;
  const regenerateState = actionState(REGENERATE_ACTION, busy, session.can_generate);
  const hinted = stale ? hintId : undefined;
  const save = saveButton(version, session.result_stale, withSources);
  return (
    <section className="card side-card stack" aria-label="결과 다음 할 일">
      <h2>{heading}</h2>
      {session.error && (
        <p className="error" role="alert">
          {session.error}
        </p>
      )}
      <FlowSummary flow={session.flow} />
      <SupplementPanel {...supplements} busy={busy} />
      <div className="stack8">
        {evidence && (
          <button type="button" className={evidence.primary ? "btn primary full" : "btn full"} disabled={busy} onClick={evidence.onReview}>
            {evidence.label}
          </button>
        )}
        {!stale && (
          <button type="button" className="btn full" disabled={regenerateState.disabled} onClick={onRegenerate}>
            {regenerateState.label}
          </button>
        )}
        <button
          type="button"
          className={save.primary ? "btn primary full" : "btn full"}
          disabled={busy || save.disabled}
          aria-describedby={hinted}
          onClick={onSave}
        >
          {save.label}
        </button>
        {onEditText && (
          <button type="button" className="btn full" disabled={busy} onClick={onEditText}>
            소개 문구 수정하기
          </button>
        )}
        {onChangeAnswers && (
          <button type="button" className="btn full" disabled={busy} onClick={onChangeAnswers}>
            기준 답변 바꾸기
          </button>
        )}
        {onBeforeEvidence && (
          <button type="button" className="btn full" disabled={busy} onClick={onBeforeEvidence}>
            근거 반영 전 보기
          </button>
        )}
        <button type="button" className="btn full" disabled={busy} onClick={onContinue}>
          질문 이어 가기
        </button>
        <button type="button" className="btn full" disabled={busy || stale} aria-describedby={hinted} onClick={() => onDownload("html")}>
          문서 내려받기
        </button>
      </div>
      {stale && (
        <p id={hintId} className="small muted">
          {STALE_SAVE_HINT}
        </p>
      )}
      <p className="small muted">AI 제안과 외부 사실은 따로 검토가 필요해요.</p>
    </section>
  );
}
