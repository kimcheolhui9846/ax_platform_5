import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";

import type { SessionSummary } from "../api/types";
import { canRename, NAME_MAX } from "../lib/sessions";

type FormProps = { titleId: string; name: string; busy: boolean; onCancel: () => void };

/** 작업 이름 바꾸기 양식. 입력 중인 글은 이 양식이 가진다. */
export function RenameForm({ titleId, name, busy, onSave, onCancel }: FormProps & { onSave: (name: string) => void }) {
  const [text, setText] = useState(name);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!busy && canRename(text)) onSave(text.trim());
  };
  return (
    <form className="stack" onSubmit={submit}>
      <h2 id={titleId}>작업 이름 바꾸기</h2>
      <input
        aria-labelledby={titleId}
        maxLength={NAME_MAX}
        value={text}
        autoComplete="off"
        autoFocus
        onChange={(event) => setText(event.target.value)}
      />
      <div className="row dialog-footer">
        <button type="button" className="btn" disabled={busy} onClick={onCancel}>
          취소
        </button>
        <button type="submit" className="btn primary grow" disabled={busy || !canRename(text)}>
          저장
        </button>
      </div>
    </form>
  );
}

/** 작업 삭제 확인. */
export function DeleteConfirm({ titleId, name, busy, onDelete, onCancel }: FormProps & { onDelete: () => void }) {
  return (
    <div className="stack">
      <h2 id={titleId}>{`"${name}" 작업을 삭제할까요?`}</h2>
      <p className="muted">질문·결과·저장한 버전이 모두 지워지고 되돌릴 수 없어요.</p>
      <div className="row dialog-footer">
        <button type="button" className="btn" disabled={busy} onClick={onCancel}>
          취소
        </button>
        <button type="button" className="btn primary grow" disabled={busy} onClick={onDelete}>
          삭제
        </button>
      </div>
    </div>
  );
}

type Props = {
  summary: SessionSummary;
  busy: boolean;
  onRename: (name: string) => void;
  onDelete: () => void;
};

type Open = "rename" | "delete" | null;

/**
 * 작업 항목의 '이름 바꾸기'·'삭제' 버튼과 모달. 어느 쪽이든 확인을 누르면 요청을 보내고 닫는다.
 * 이름은 닫히면 연 버튼으로 포커스를 돌려준다(삭제는 항목이 사라지므로 부른 쪽이 정한다).
 */
export function WorkItemActions({ summary, busy, onRename, onDelete }: Props) {
  const [open, setOpen] = useState<Open>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const renameButton = useRef<HTMLButtonElement>(null);
  const refocus = useRef(false); // 닫힌 뒤 열었던 버튼으로 포커스를 돌려줄 차례
  const titleId = useId();

  useEffect(() => {
    const node = dialog.current;
    if (node === null) return;
    if (open !== null && !node.open) {
      node.showModal();
      node.querySelector("input")?.focus();
    }
    if (open === null && node.open) node.close();
  }, [open]);

  // 저장 요청 중에는 버튼이 막혀 포커스를 받지 못하므로, 요청이 끝난 뒤(busy 해제)에 돌려준다.
  useEffect(() => {
    if (open === null && !busy && refocus.current) {
      refocus.current = false;
      renameButton.current?.focus();
    }
  }, [open, busy]);

  const close = () => setOpen(null);
  const closeRename = () => {
    refocus.current = true;
    close();
  };
  return (
    <div className="item-actions">
      <button
        ref={renameButton}
        type="button"
        className="btn compact"
        aria-label={`${summary.name} 이름 바꾸기`}
        disabled={busy} onClick={() => setOpen("rename")}>
        이름 바꾸기
      </button>
      <button type="button" className="btn compact" aria-label={`${summary.name} 삭제`} disabled={busy} onClick={() => setOpen("delete")}>
        삭제
      </button>
      <dialog
        ref={dialog}
        className="dialog"
        aria-labelledby={titleId}
        onCancel={(event) => {
          event.preventDefault();
          if (open === "rename") closeRename();
          else close();
        }}
      >
        {open === "rename" && (
          <RenameForm
            titleId={titleId}
            name={summary.name}
            busy={busy}
            onSave={(name) => {
              closeRename();
              onRename(name);
            }}
            onCancel={closeRename}
          />
        )}
        {open === "delete" && (
          <DeleteConfirm
            titleId={titleId}
            name={summary.name}
            busy={busy}
            onDelete={() => {
              close();
              onDelete();
            }}
            onCancel={close}
          />
        )}
      </dialog>
    </div>
  );
}
