import type { FlowItem } from "../api/types";
import { flowNote, flowNumber, flowStatusLabel, isEditable } from "../lib/flowView";

type Props = {
  modeLabel: string;
  position: string;
  request: string;
  flow: FlowItem[];
  atConfirm: boolean;
  busy: boolean;
  onEdit: (questionId: string) => void;
  onPrevious: (() => void) | null;
};

/** 오른쪽 질문과 답변 흐름: 01 요청 → 물어본 질문 → 지금 질문 → 예정 → 답변 확인. */
export function FlowPanel({ modeLabel, position, request, flow, atConfirm, busy, onEdit, onPrevious }: Props) {
  return (
    <section className="card side-card flow-panel stack12" aria-label="질문과 답변 흐름">
      <h2>질문과 답변 흐름</h2>
      <p className="muted">{`${modeLabel} · ${position}`}</p>
      <div className="flow-item">
        <p className="label">01 요청 정리 · 완료</p>
        <p>{request}</p>
      </div>
      {flow.map((item, index) => (
        <div
          key={item.field}
          className={item.status === "current" ? "flow-item is-current" : "flow-item"}
          aria-current={item.status === "current" ? "step" : undefined}
        >
          <div className="row">
            <p className="label grow">{`${flowNumber(index)} ${item.label} · ${flowStatusLabel(item.status)}`}</p>
            {isEditable(item) && (
              <button
                type="button"
                className="btn textbtn"
                disabled={busy}
                aria-label={`${item.label} 답변 수정`}
                onClick={() => onEdit(item.question.question_id)}
              >
                수정
              </button>
            )}
          </div>
          <p>{item.text}</p>
          <p className="muted">{flowNote(item)}</p>
        </div>
      ))}
      <div className="flow-item">
        <p className="label">{`${atConfirm ? "현재" : "다음"} · 답변 확인 → 초안 만들기`}</p>
        <p className="muted">아직 정하지 않은 정보는 미정으로 남겨 두고 초안을 만들 수 있어요.</p>
      </div>
      {onPrevious && (
        <button type="button" className="btn full" disabled={busy} onClick={onPrevious}>
          ← 이전 단계
        </button>
      )}
    </section>
  );
}
