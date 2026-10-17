import { useEffect, useId, useRef, useState } from "react";

import type { SupplementItem } from "../api/types";
import { supplementStatus } from "../lib/supplements";
import { SupplementForm } from "./SupplementForm";

type Props = {
  current: SupplementItem[]; // 지금 입력(세션)
  applied: SupplementItem[]; // 지금 결과에 반영한 값
  changed: boolean; // 입력이 아직 결과에 반영되지 않았다
  busy: boolean;
  onSave: (values: Record<string, string | null>) => void;
  onApply: () => void;
};

/**
 * 결과 오른쪽의 '미확인 정보 채우기'와 입력 대화상자. 대화상자가 열렸는지는 이 부품 안에서 끝나는 UI 상태라 여기서 가진다.
 * 닫으면(취소·저장·Esc) 연 버튼으로 포커스를 돌려준다. 보완 항목이 없는 과제면 그리지 않는다.
 */
export function SupplementPanel({ current, applied, changed, busy, onSave, onApply }: Props) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    const node = dialog.current;
    if (node === null) return;
    if (open && !node.open) node.showModal();
    if (!open && node.open) node.close();
  }, [open]);

  if (current.length === 0) return null;
  const status = supplementStatus(current, applied, changed);
  const close = () => {
    setOpen(false);
    opener.current?.focus();
  };

  return (
    <section className="info-panel stack8" aria-label="미확인 정보 채우기">
      <h3>미확인 정보 채우기</h3>
      <p>{status.line}</p>
      <p className="small muted">{status.missing}</p>
      <div className="info-actions">
        <button ref={opener} type="button" className="btn" disabled={busy} onClick={() => setOpen(true)}>
          정보 입력·수정
        </button>
        <button type="button" className="btn" disabled={busy || !status.canApply} onClick={onApply}>
          초안에 반영
        </button>
      </div>
      <dialog
        ref={dialog}
        className="dialog"
        aria-labelledby={titleId}
        onCancel={(event) => {
          event.preventDefault(); // Esc도 같은 길(close)로 닫는다
          close();
        }}
      >
        {open && (
          <SupplementForm
            titleId={titleId}
            items={current}
            busy={busy}
            onSave={(values) => {
              onSave(values);
              close();
            }}
            onCancel={close}
          />
        )}
      </dialog>
    </section>
  );
}
