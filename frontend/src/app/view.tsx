import type { JSX } from "react";

import type { AnswerBody, CoachingMode, ResultView, ReviseBody, SessionSummary, SessionView, TaskSummary } from "../api/types";
import { FlowPanel } from "../components/FlowPanel";
import { QuestionCard } from "../components/QuestionCard";
import { ReviseCard } from "../components/ReviseCard";
import { AppShell } from "../layout/AppShell";
import { firstSectionOrder } from "../lib/document";
import type { DocumentFile } from "../lib/document";
import { answeredBefore, firstEditable, previousEditable, questionPosition } from "../lib/flowView";
import { modeName } from "../lib/modes";
import { isPrivate } from "../lib/privacy";
import { questionKicker } from "../lib/question";
import { appliedSourceIds, evidenceButton, resultHeading, versionBeforeEvidence } from "../lib/evidence";
import type { ExampleAction } from "../lib/question";
import type { CarrySource } from "../lib/carry";
import type { Route } from "../lib/routes";
import { versionIsStale } from "../lib/sessions";
import { enabledNav, railActive, railItems, routePhase } from "../lib/shell";
import type { NavKey } from "../lib/shell";
import { ConfirmScreen } from "../screens/ConfirmScreen";
import { FailedMain, FailedSide, GeneratingMain, GeneratingSide } from "../screens/GenerationScreens";
import { DocumentsScreen } from "../screens/DocumentsScreen";
import { EditMain, EditSide } from "../screens/EditScreen";
import { EvidenceMain, EvidenceSide } from "../screens/EvidenceScreen";
import { GuideScreen } from "../screens/GuideScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { ModeScreen } from "../screens/ModeScreen";
import { RequestScreen } from "../screens/RequestScreen";
import { ResultMain, ResultSide } from "../screens/ResultScreen";
import { SavedMain, SavedSide } from "../screens/SavedScreen";
import { LoadingScreen, UnavailableScreen } from "../screens/StatusScreens";
import { VersionMain, VersionSide } from "../screens/VersionScreen";
import { WorkScreen } from "../screens/WorkScreen";
import { documentFileOf } from "./documentFile";
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
  example: (action: ExampleAction["action"], isPrivate: boolean) => void; // isPrivate: 질문 카드의 비공개 체크('다른 예시 보기'에 실린다)
  earlyDraft: () => void;
  edit: (questionId: string) => void;
  revise: (questionId: string, body: ReviseBody) => void;
  backToQuestions: () => void;
  generate: () => void;
  showResult: () => void;
  confirm: () => void;
  continueQuestions: () => void;
  resume: (summary: SessionSummary) => void;
  openVersion: (sessionId: string, version: number) => void;
  saveVersion: () => void;
  saveSupplements: (values: Record<string, string | null>, privacy: Record<string, boolean>) => void;
  acknowledgeNotice: (task: string, acknowledged: boolean) => void;
  applySupplements: () => void;
  editSection: (order: number) => void;
  submitEdit: (order: number, text: string) => void;
  download: (file: DocumentFile) => void;
  reviewEvidence: () => void;
  applyEvidence: (sourceId: string) => void;
  openBeforeEvidence: () => void;
  startNext: (task: string, from: CarrySource) => void;
  dropCarry: (task: string) => void;
  clearContext: () => void;
};

export type ScreenParts = { main: JSX.Element; side: JSX.Element | null };

/** 화면 모델 → 본문과 오른쪽 패널. 판단은 하지 않고 모델과 lib의 순수 함수로만 그린다. */
export function renderScreen(model: ScreenModel, busy: boolean, on: Handlers): ScreenParts {
  const file = documentFileOf(model);
  const download = () => {
    if (file) on.download(file);
  };
  switch (model.kind) {
    case "generating":
      return { main: <GeneratingMain />, side: <GeneratingSide flow={model.session.flow} /> };
    case "failed":
      return {
        main: (
          <FailedMain
            hasResult={model.session.has_result}
            busy={busy}
            canGenerate={model.session.can_generate}
            onRetry={on.generate}
            onConfirm={on.confirm}
            onShowResult={on.showResult}
          />
        ),
        side: <FailedSide flow={model.session.flow} />,
      };
    case "loading":
      return { main: <LoadingScreen />, side: null };
    case "evidence":
      return {
        main: <EvidenceMain items={model.items} />,
        side: (
          <EvidenceSide
            flow={model.session.flow}
            items={model.items}
            applied={appliedSourceIds(model.result.result.evidence)}
            busy={busy}
            onApply={on.applyEvidence}
            onBack={on.showResult}
          />
        ),
      };
    case "unavailable":
      return { main: <UnavailableScreen onRetry={on.retry} onHome={on.goHome} />, side: null };
    case "home":
      return {
        main: (
          <HomeScreen
            tasks={model.tasks}
            sessions={model.sessions}
            onStart={on.start}
            onResume={on.resume}
            onWork={() => on.navigate("work")}
          />
        ),
        side: null,
      };
    case "guide":
      return { main: <GuideScreen onStart={on.goHome} />, side: null };
    case "work":
      return { main: <WorkScreen sessions={model.sessions} onResume={on.resume} onHome={on.goHome} />, side: null };
    case "documents":
      return { main: <DocumentsScreen sessions={model.sessions} onOpen={on.openVersion} onHome={on.goHome} />, side: null };
    case "request": {
      const task = model.task.task_type;
      return {
        main: (
          <RequestScreen
            task={model.task}
            form={model.form}
            draft={model.draft}
            context={model.context}
            carryFailed={model.carryFailed}
            acknowledged={model.noticeAcknowledged}
            busy={busy}
            onAcknowledge={(acknowledged) => on.acknowledgeNotice(task, acknowledged)}
            onExcludeContext={() => on.dropCarry(task)}
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
            context={model.context}
            carryFailed={model.carryFailed}
            acknowledged={model.noticeAcknowledged}
            onExcludeContext={() => on.dropCarry(task)}
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
            kicker={questionKicker(model.question, answeredBefore(model.session.flow))}
            request={model.session.raw_input}
            defaultPrivate={isPrivate(model.session.private_names, model.question.field)}
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
            defaultPrivate={isPrivate(model.session.private_names, model.item.field)}
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
            onClearContext={on.clearContext}
          />
        ),
        side: flowSide(model.session, true, busy, on),
      };
    }
    case "result": {
      const editable = firstEditable(model.session.flow);
      return {
        main: <ResultMain task={model.task} session={model.session} result={model.result} images={model.images} busy={busy} onConfirm={on.confirm} onRegenerate={on.generate} />,
        side:
          model.result === null ? null : (
            <ResultSide
              session={model.session}
              version={model.result.version}
              heading={resultHeading(model.result.version.reason)}
              withSources={model.result.result.evidence.length > 0}
              evidence={evidenceAction(model.task, model.result, on)}
              onBeforeEvidence={versionBeforeEvidence(model.result.version) === null ? null : on.openBeforeEvidence}
              busy={busy}
              supplements={supplementProps(model.session, model.result, on)}
              onEditText={editTextOf(model.result, on)}
              onRegenerate={on.generate}
              onSave={on.saveVersion}
              onChangeAnswers={editable ? () => on.edit(editable) : null}
              onContinue={on.continueQuestions}
              onDownload={download}
            />
          ),
      };
    }
    case "edit": {
      const order = model.section.order;
      return {
        main: (
          <EditMain
            key={`${model.result.version.version}-${order}`}
            section={model.section}
            busy={busy}
            onSubmit={(text) => on.submitEdit(order, text)}
            onBack={on.showResult}
          />
        ),
        side: <EditSide flow={model.session.flow} supplements={supplementProps(model.session, model.result, on)} busy={busy} />,
      };
    }
    case "saved":
      return {
        main: (
          <SavedMain
            task={model.task}
            version={model.version}
            next={savedNext(model, on)}
            onDocuments={() => on.navigate("documents")}
            onOpen={() => on.openVersion(model.session.session_id, model.version.version.version)}
            onDownload={download}
          />
        ),
        side: <SavedSide session={model.session} />,
      };
    case "version":
      return {
        main: (
          <VersionMain
            task={model.task}
            version={model.version}
            stale={versionIsStale(model.version, model.session)}
            images={model.images}
            onCurrent={on.showResult}
          />
        ),
        side: <VersionSide version={model.version} onDocuments={() => on.navigate("documents")} onDownload={download} />,
      };
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

/** 저장 완료의 '이 결과로 ○○ 시작': 다음 과제가 없으면 없다. */
function savedNext(model: Extract<ScreenModel, { kind: "saved" }>, on: Handlers) {
  const next = model.next;
  if (next === null) return null;
  const from = { sessionId: model.session.session_id, version: model.version.version.version };
  return { title: next.title, onStart: () => on.startNext(next.task_type, from) };
}

/** 보완 패널에 넘길 값: 지금 입력과 미반영 여부는 세션, 반영한 값은 지금 결과의 것이다. */
function supplementProps(session: SessionView, result: ResultView, on: Handlers) {
  return {
    current: session.supplements,
    applied: result.supplements,
    changed: session.supplements_changed,
    canGenerate: session.can_generate,
    onSave: on.saveSupplements,
    onApply: on.applySupplements,
  };
}

/** 결과 화면의 근거 버튼. 자료가 없는 과제면 없다. */
function evidenceAction(task: TaskSummary, result: ResultView, on: Handlers) {
  const button = evidenceButton(task.evidence_sources, result.result.evidence.length > 0);
  return button === null ? null : { ...button, onReview: on.reviewEvidence };
}

/** 결과 화면의 '소개 문구 수정하기': 첫 섹션을 연다. 섹션이 없으면 버튼을 두지 않는다. */
function editTextOf(result: ResultView, on: Handlers): (() => void) | null {
  const order = firstSectionOrder(result.result.sections);
  return order === null ? null : () => on.editSection(order);
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
