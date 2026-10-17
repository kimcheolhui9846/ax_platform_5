import { useState } from "react";
import type { FormEvent } from "react";

import type { SupplementItem } from "../api/types";
import { supplementDraft, supplementValues } from "../lib/supplements";

type Props = {
  titleId: string; // 대화상자 제목 id(aria-labelledby). 미리보기는 프레임마다 다른 id를 준다
  items: SupplementItem[];
  busy: boolean;
  onSave: (values: Record<string, string | null>) => void;
  onCancel: () => void;
};

/** 미확인 정보 입력 양식. 입력 중인 값은 이 양식이 가진다. 빈 칸은 미확인으로 저장한다. */
export function SupplementForm({ titleId, items, busy, onSave, onCancel }: Props) {
  const [draft, setDraft] = useState(() => supplementDraft(items));
  const set = (name: string, text: string) => setDraft((current) => ({ ...current, [name]: text }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!busy) onSave(supplementValues(draft));
  };
  return (
    <form className="supplement-form stack" onSubmit={submit}>
      <div className="row">
        <div className="grow stack8">
          <p className="small">추가 정보 입력</p>
          <h2 id={titleId}>미확인 정보를 채워 주세요</h2>
        </div>
        <button type="button" className="btn compact" aria-label="정보 입력 닫기" onClick={onCancel}>
          닫기
        </button>
      </div>
      <p className="muted">모르는 항목은 비워 두어도 괜찮아요. 입력 내용은 저장 후 초안에 따로 반영합니다.</p>
      {items.map((item) => {
        const id = `${titleId}-${item.name}`;
        return (
          <div key={item.name} className="field-row">
            <label htmlFor={id}>{item.label}</label>
            <input
              id={id}
              maxLength={250}
              value={draft[item.name] ?? ""}
              placeholder="미확인"
              autoComplete="off"
              onChange={(event) => set(item.name, event.target.value)}
            />
            <div className="field-actions">
              <button type="button" className="btn compact" disabled={item.example === ""} onClick={() => set(item.name, item.example)}>
                예시 넣기
              </button>
              <button type="button" className="btn compact" onClick={() => set(item.name, "")}>
                미확인으로
              </button>
            </div>
          </div>
        );
      })}
      <p className="small muted">입력값은 사용자 제공 정보입니다. 예시값을 선택해도 사실 검증이 완료된 것은 아니에요.</p>
      <div className="row dialog-footer">
        <button type="button" className="btn" onClick={onCancel}>
          취소
        </button>
        <button type="submit" className="btn primary grow" disabled={busy}>
          입력 내용 저장
        </button>
      </div>
    </form>
  );
}
