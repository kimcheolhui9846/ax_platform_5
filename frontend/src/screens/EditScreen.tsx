import { useState } from "react";

import type { FlowItem, ResultSection, SupplementItem } from "../api/types";
import { Composer } from "../components/Composer";
import { FlowSummary } from "../components/FlowSummary";
import { SupplementPanel } from "../components/SupplementPanel";
import { sectionText } from "../lib/document";

type MainProps = { section: ResultSection; busy: boolean; onSubmit: (text: string) => void; onBack: () => void };

/** 결과 섹션 하나의 문구를 고친다. 입력 중인 글은 이 화면이 가진다(부모가 key로 새로 만든다). */
export function EditMain({ section, busy, onSubmit, onBack }: MainProps) {
  const current = sectionText(section);
  const [text, setText] = useState(current);
  return (
    <section className="card edit-card stack" aria-label="문구 수정">
      <p className="small">{`소개 문구 수정 · ${section.heading}`}</p>
      <h1>문구를 다듬어 볼까요?</h1>
      <div className="notice stack8">
        <p className="muted">지금 문구</p>
        <p className="bodycopy">{current}</p>
      </div>
      <Composer
        label="바꿀 문구를 직접 입력해 주세요"
        value={text}
        placeholder="바꿀 문구"
        rows={5}
        maxLength={2500}
        submitLabel="문구 반영하기"
        busy={busy}
        onChange={setText}
        onSubmit={onSubmit}
      />
      <p className="muted">이 항목의 문구만 바꿔요. 선택한 답변, 보완 정보, 근거 검토 기록은 그대로예요.</p>
      <button type="button" className="btn" disabled={busy} onClick={onBack}>
        ← 결과로 돌아가기
      </button>
    </section>
  );
}

/** 보완 패널에 넘기는 값(busy는 따로). 결과 화면과 문구 수정 화면이 같이 쓴다. */
export type SupplementProps = {
  current: SupplementItem[];
  applied: SupplementItem[];
  changed: boolean;
  onSave: (values: Record<string, string | null>) => void;
  onApply: () => void;
};

type SideProps = { flow: FlowItem[]; supplements: SupplementProps; busy: boolean };

export function EditSide({ flow, supplements, busy }: SideProps) {
  return (
    <section className="card side-card stack" aria-label="결과 기준">
      <h2>질문과 답변 흐름</h2>
      <FlowSummary flow={flow} />
      <SupplementPanel {...supplements} busy={busy} />
    </section>
  );
}
