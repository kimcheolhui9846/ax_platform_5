import { useEffect, useId, useReducer, useRef } from "react";

import type { SupplementItem } from "../api/types";
import { panelAfter, supplementStatus } from "../lib/supplements";
import { SupplementForm } from "./SupplementForm";

type Props = {
  current: SupplementItem[]; // 지금 입력(세션)
  applied: SupplementItem[]; // 지금 결과에 반영한 값
  changed: boolean; // 입력이 아직 결과에 반영되지 않았다
  canGenerate: boolean; // 지금 초안을 만들 수 있다
  busy: boolean;
  onSave: (values: Record<string, string | null>, privacy: Record<string, boolean>) => void;
  onApply: (() => void) | null; // null이면 '초안에 반영'을 두지 않는다(문구 수정 화면)
};

/**
 * 결과 오른쪽의 '미확인 정보 채우기'와 입력 대화상자. 대화상자 단계(panelAfter)는 이 부품 안에서 끝나는 UI 상태라 여기서 가진다.
 * 저장을 누르면 연 채 저장 중으로 두고, 요청이 끝났을 때 받은 current가 저장 때와 다른 배열이면 성공으로 보고 닫는다
 * (같은 배열이면 실패라 연 채 입력을 살린다). 닫히면 연 버튼으로 포커스를 돌려준다. 보완 항목이 없는 과제면 그리지 않는다.
 */
export function SupplementPanel({ current, applied, changed, canGenerate, busy, onSave, onApply }: Props) {
  const [phase, send] = useReducer(panelAfter, "closed");
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const currentAtSave = useRef(current); // 저장을 누른 때의 current 참조
  const sawBusy = useRef(false); // 저장 요청이 실제로 시작(busy)된 뒤에만 끝남을 센다
  const prevPhase = useRef(phase);

  useEffect(() => {
    const node = dialog.current;
    if (node === null) return;
    const shouldOpen = phase !== "closed";
    if (shouldOpen && !node.open) {
      node.showModal();
      node.querySelector("input")?.focus(); // 첫 입력칸(대화상자가 열린 뒤에야 포커스가 들어간다)
    }
    if (!shouldOpen && node.open) node.close();
  }, [phase]);

  useEffect(() => {
    if (phase !== "saving") {
      sawBusy.current = false;
    } else if (busy) {
      sawBusy.current = true;
    } else if (sawBusy.current) {
      send({ type: "settled", saved: current !== currentAtSave.current });
    }
  }, [phase, busy, current]);

  useEffect(() => {
    if (prevPhase.current !== "closed" && phase === "closed") opener.current?.focus();
    prevPhase.current = phase;
  }, [phase]);

  if (current.length === 0) return null;
  const status = supplementStatus(current, applied, changed, canGenerate);

  return (
    <section className="info-panel stack8" aria-label="미확인 정보 채우기">
      <h3>미확인 정보 채우기</h3>
      <p>{status.line}</p>
      <p className="small muted">{status.missing}</p>
      <div className="info-actions">
        <button ref={opener} type="button" className="btn" disabled={busy} onClick={() => send({ type: "open" })}>
          정보 입력·수정
        </button>
        {onApply !== null && (
          <button type="button" className="btn" disabled={busy || !status.canApply} onClick={onApply}>
            초안에 반영
          </button>
        )}
      </div>
      <dialog
        ref={dialog}
        className="dialog"
        aria-labelledby={titleId}
        onCancel={(event) => {
          event.preventDefault(); // Esc도 같은 길로 닫는다(저장 중에는 무시)
          send({ type: "cancel" });
        }}
      >
        {phase !== "closed" && (
          <SupplementForm
            titleId={titleId}
            items={current}
            busy={busy}
            onSave={(values, privacy) => {
              currentAtSave.current = current;
              onSave(values, privacy);
              send({ type: "save" });
            }}
            onCancel={() => send({ type: "cancel" })}
          />
        )}
      </dialog>
    </section>
  );
}
