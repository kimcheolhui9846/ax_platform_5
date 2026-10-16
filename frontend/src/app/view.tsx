import type { JSX } from "react";

import type { AnswerBody, CoachingMode, ReviseBody, SessionView } from "../api/types";
import { FlowPanel } from "../components/FlowPanel";
import { QuestionCard } from "../components/QuestionCard";
import { ReviseCard } from "../components/ReviseCard";
import { AppShell } from "../layout/AppShell";
import { firstEditable, previousEditable, questionPosition } from "../lib/flowView";
import { modeName } from "../lib/modes";
import { questionKicker } from "../lib/question";
import type { ExampleAction } from "../lib/question";
import type { Route } from "../lib/routes";
import { enabledNav, railActive, railItems, routePhase } from "../lib/shell";
import type { NavKey } from "../lib/shell";
import { ConfirmScreen } from "../screens/ConfirmScreen";
import { GuideScreen } from "../screens/GuideScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { ModeScreen } from "../screens/ModeScreen";
import { RequestScreen } from "../screens/RequestScreen";
import { ResultMain, ResultSide } from "../screens/ResultScreen";
import { LoadingScreen, UnavailableScreen } from "../screens/StatusScreens";
import type { ScreenModel } from "./screenModel";

/** 화면 버튼이 부르는 동작. 앱은 handlers.ts의 makeHandlers가, 미리보기는 NOOP_HANDLERS가 준다. */
export type Handlers = {
  navigate: (key: NavKey) => void;
  guide: () => void;
  goHome: () => void;
  retry: () => void;
  start: (task: string) => void;
  changeDraft: (task: string, text: string) => void;
  submitRequest: (task: string) => void;
  editRequest: (task: string) => void;
  pickMode: (task: string, mode: CoachingMode) => void;
  answer: (body: AnswerBody) => void;
  example: (action: ExampleAction["action"]) => void;
  earlyDraft: () => void;
  edit: (questionId: string) => void;
  revise: (questionId: string, body: ReviseBody) => void;
  backToQuestions: () => void;
  generate: () => void;
  showResult: () => void;
  confirm: () => void;
  continueQuestions: () => void;
};

export type ScreenParts = { main: JSX.Element; side: JSX.Element | null };

/** 화면 모델 → 본문과 오른쪽 패널. 판단은 하지 않고 모델과 lib의 순수 함수로만 그린다. */
export function renderScreen(model: ScreenModel, busy: boolean, on: Handlers): ScreenParts {
  switch (model.kind) {
    case "loading":
      return { main: <LoadingScreen />, side: null };
    case "unavailable":
      return { main: <UnavailableScreen onRetry={on.retry} onHome={on.goHome} />, side: null };
    case "home":
      return { main: <HomeScreen tasks={model.tasks} onStart={on.start} />, side: null };
    case "guide":
      return { main: <GuideScreen onStart={on.goHome} />, side: null };
    case "request": {
      const task = model.task.task_type;
      return {
        main: (
          <RequestScreen
            task={model.task}
            form={model.form}
            draft={model.draft}
            onChange={(text) => on.changeDraft(task, text)}
            onSubmit={() => on.submitRequest(task)}
          />
        ),
        side: null,
      };
    }
    case "mode": {
      const task = model.task.task_type;
      return {
        main: (
          <ModeScreen
            form={model.form}
            draft={model.draft}
            busy={busy}
            onPick={(mode) => on.pickMode(task, mode)}
            onEditRequest={() => on.editRequest(task)}
          />
        ),
        side: null,
      };
    }
    case "question":
      return {
        main: (
          <QuestionCard
            key={model.question.question_id}
            question={model.question}
            kicker={questionKicker(model.question, model.session.progress.asked)}
            request={model.session.raw_input}
            busy={busy}
            onAnswer={on.answer}
            onExample={on.example}
            onEarlyDraft={on.earlyDraft}
          />
        ),
        side: flowSide(model.session, false, busy, on),
      };
    case "revise": {
      const questionId = model.item.question.question_id;
      return {
        main: (
          <ReviseCard
            key={questionId}
            item={model.item}
            busy={busy}
            onRevise={(body) => on.revise(questionId, body)}
            onCancel={on.backToQuestions}
          />
        ),
        side: flowSide(model.session, false, busy, on),
      };
    }
    case "confirm": {
      const editable = firstEditable(model.session.flow);
      return {
        main: (
          <ConfirmScreen
            task={model.task}
            session={model.session}
            busy={busy}
            onAct={(action) => (action === "generate" ? on.generate() : on.showResult())}
            onChangeAnswers={editable ? () => on.edit(editable) : null}
            onBackToQuestion={model.session.next_question ? on.backToQuestions : null}
          />
        ),
        side: flowSide(model.session, true, busy, on),
      };
    }
    case "result": {
      const editable = firstEditable(model.session.flow);
      return {
        main: <ResultMain task={model.task} session={model.session} result={model.result} busy={busy} onConfirm={on.confirm} />,
        side:
          model.result === null ? null : (
            <ResultSide
              session={model.session}
              busy={busy}
              onRegenerate={on.generate}
              onChangeAnswers={editable ? () => on.edit(editable) : null}
              onContinue={on.continueQuestions}
            />
          ),
      };
    }
  }
}

function flowSide(session: SessionView, atConfirm: boolean, busy: boolean, on: Handlers): JSX.Element {
  const previous = previousEditable(session.flow);
  return (
    <FlowPanel
      modeLabel={modeName(session.mode)}
      position={questionPosition(session.flow, session.progress.cap)}
      request={session.raw_input}
      flow={session.flow}
      atConfirm={atConfirm}
      busy={busy}
      onEdit={on.edit}
      onPrevious={previous ? () => on.edit(previous) : null}
    />
  );
}

/** 헤더의 과제 이름. 과제 밖 화면은 null이다. */
export function projectOf(model: ScreenModel): string | null {
  return "task" in model ? model.task.title : null;
}

export function pageTitle(model: ScreenModel): string {
  const project = projectOf(model);
  return project ? `창작자 AX · ${project}` : "창작자 AX";
}

type ViewProps = { route: Route; model: ScreenModel; busy: boolean; on: Handlers; mainId?: string };

/** 뼈대까지 그린 화면 하나. 앱과 미리보기 갤러리가 같이 쓴다(갤러리는 프레임마다 mainId를 바꾼다). */
export function AppView({ route, model, busy, on, mainId }: ViewProps) {
  const { main, side } = renderScreen(model, busy, on);
  return (
    <AppShell
      rail={{
        items: railItems(railActive(route), enabledNav(busy)),
        onNavigate: on.navigate,
        onGuide: on.guide,
        guideDisabled: busy,
      }}
      header={{ project: projectOf(model), phase: routePhase(route), onPickTask: on.goHome, pickDisabled: busy }}
      side={side}
      mainId={mainId}
    >
      {main}
    </AppShell>
  );
}
