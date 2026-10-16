import type { JSX } from "react";

import { IdeaForm } from "../components/IdeaForm";
import { QuestionCard } from "../components/QuestionCard";
import { ResultPanel } from "../components/ResultPanel";
import { SummaryList } from "../components/SummaryList";
import { TaskPicker } from "../components/TaskPicker";
import { AppShell } from "../layout/AppShell";
import type { HeaderProps } from "../layout/Header";
import { railItems } from "../lib/shell";
import type { NavKey, Phase } from "../lib/shell";
import { RESULT, SESSION_CLARIFYING, SESSION_LADDER, SESSION_READY, TASKS } from "./fixtures";

export type Frame = { id: string; title: string; render: () => JSX.Element };

export const FRAME_WIDTHS = { desktop: 1512, mobile: 390 } as const;

const noop = () => {};
const ENABLED = new Set<NavKey>(["home"]);

function shell(project: string | null, phase: Phase | null, body: JSX.Element, side: JSX.Element | null = null) {
  const header: HeaderProps = { project, phase, onPickTask: noop };
  return (
    <AppShell rail={{ items: railItems(phase === null ? "home" : null, ENABLED), onNavigate: noop }} header={header} side={side}>
      {body}
    </AppShell>
  );
}

/** 갤러리에 그릴 화면 상태. 묶음이 늘 때마다 여기에 상태를 더한다. */
export const FRAMES: Frame[] = [
  { id: "home", title: "홈 · 과제 선택", render: () => shell(null, null, <TaskPicker tasks={TASKS} onPick={noop} />) },
  {
    id: "idea",
    title: "요청 입력",
    render: () =>
      shell("상품기획", 0, <IdeaForm title="상품기획" value="한글을 활용한 파우치를 만들고 싶어요" busy={false} onChange={noop} onSubmit={noop} />),
  },
  {
    id: "question",
    title: "질문 · 기본",
    render: () =>
      shell(
        "상품기획",
        1,
        <QuestionCard question={SESSION_CLARIFYING.next_question!} busy={false} onAnswer={noop} />,
        <SummaryList items={SESSION_CLARIFYING.summary} />,
      ),
  },
  {
    id: "question-ladder",
    title: "질문 · 다른 예시(쉬운 질문)",
    render: () =>
      shell(
        "상품기획",
        1,
        <QuestionCard question={SESSION_LADDER.next_question!} busy={false} onAnswer={noop} />,
        <SummaryList items={SESSION_LADDER.summary} />,
      ),
  },
  {
    id: "ready",
    title: "답변 확인 · 결과 만들기 전",
    render: () => shell("상품기획", 1, <p className="card">필요한 정보가 모였어요. 결과를 만들어 볼까요?</p>, <SummaryList items={SESSION_READY.summary} />),
  },
  { id: "result", title: "결과 문서", render: () => shell("상품기획", 2, <ResultPanel view={RESULT} busy={false} onBack={noop} />) },
];
