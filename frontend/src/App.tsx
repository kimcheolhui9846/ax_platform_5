import { useEffect, useState } from "react";

import { BACKEND_UNREACHABLE, toOutcome } from "./api/client";
import type { ApiResult } from "./api/client";
import {
  continueSession,
  createSession,
  generateResult,
  getResult,
  getSession,
  listTasks,
  submitAnswer,
} from "./api/coaching";
import type { AnswerBody, ResultView, SessionView, TaskSummary } from "./api/types";
import { ActionButton } from "./components/ActionButton";
import { IdeaForm } from "./components/IdeaForm";
import { LegacyQuestionCard as QuestionCard } from "./components/LegacyQuestionCard";
import { ResultPanel } from "./components/ResultPanel";
import { SummaryList } from "./components/SummaryList";
import { TaskPicker } from "./components/TaskPicker";
import { AppShell } from "./layout/AppShell";
import { formatProgress } from "./lib/progress";
import { STALE_HINT, screenOf, sessionActions } from "./lib/screen";
import type { SessionAction } from "./lib/screen";
import { enabledNav, phaseOf, railItems } from "./lib/shell";
import type { NavKey } from "./lib/shell";

/** 화면 상태(과제, 세션, 결과)와 요청 상태(busy/error)는 이 컴포넌트에서만 바꾼다. 어떤 화면인지는 screenOf가 정한다. */
export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [task, setTask] = useState<TaskSummary | null>(null);
  const [rawInput, setRawInput] = useState("");
  const [session, setSession] = useState<SessionView | null>(null);
  const [result, setResult] = useState<ResultView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run<T>(request: () => Promise<ApiResult<T>>, onData: (data: T) => void, onFail?: () => void) {
    setBusy(true);
    setError(null);
    try {
      const outcome = toOutcome(await request());
      if (outcome.ok) onData(outcome.data);
      else {
        setError(outcome.message);
        onFail?.();
      }
    } catch {
      setError(BACKEND_UNREACHABLE);
    } finally {
      setBusy(false);
    }
  }

  /** 실패 뒤 서버의 세션 상태(FAILED 등)를 다시 받아 온다. 오류 문구는 건드리지 않는다. */
  async function refreshSession(sessionId: string) {
    try {
      const outcome = toOutcome(await getSession(sessionId));
      if (outcome.ok) setSession(outcome.data);
    } catch {
      // 연결 오류는 이미 보여 준 오류 문구로 충분하다.
    }
  }

  useEffect(() => {
    void run(listTasks, setTasks);
  }, []);

  function startSession() {
    if (!task) return;
    void run(() => createSession(task.task_type, rawInput), setSession);
  }

  function answer(body: AnswerBody) {
    if (!session?.next_question) return;
    const { session_id } = session;
    const { question_id } = session.next_question;
    void run(() => submitAnswer(session_id, question_id, body), setSession);
  }

  function generate() {
    if (!session) return;
    const { session_id } = session;
    void run(() => generateResult(session_id), setResult, () => void refreshSession(session_id));
  }

  /** 결과에서 질문으로 돌아간다. 남은 질문이 있으면 서버가 다음 질문을 걸어 돌려준다. */
  function backToQuestions() {
    if (!result) return;
    const { session_id } = result;
    void run(
      () => continueSession(session_id),
      (fresh) => {
        setSession(fresh);
        setResult(null);
      },
    );
  }

  function showResult() {
    if (!session) return;
    const { session_id } = session;
    void run(() => getResult(session_id), setResult);
  }

  function reset() {
    setTask(null);
    setRawInput("");
    setSession(null);
    setResult(null);
    setError(null);
  }

  /** 누를 수 있는 메뉴는 enabledNav가 정한다. 내 작업·결과물은 묶음 2에서 연다. */
  function navigate(key: NavKey) {
    if (key === "home") reset();
  }

  function act({ action }: SessionAction) {
    if (action === "show_result") showResult();
    else generate();
  }

  const screen = screenOf(task, session, result);
  const actions = "session" in screen ? sessionActions(screen.session) : null;
  const secondary = actions?.secondary ?? null;
  const banner = error ?? (screen.kind === "failed" ? screen.session.error : null);
  const question = screen.kind === "clarifying" || screen.kind === "failed" ? screen.question : null;

  return (
    <AppShell
      rail={{ items: railItems(screen.kind === "pick_task" ? "home" : null, enabledNav(busy)), onNavigate: navigate }}
      header={{ project: task?.title ?? null, phase: phaseOf(screen.kind), onPickTask: reset, pickDisabled: busy }}
    >
      {banner && <p className="error">{banner}</p>}

      {screen.kind === "pick_task" && <TaskPicker tasks={tasks} onPick={setTask} />}

      {screen.kind === "idea" && (
        <IdeaForm title={screen.task.title} value={rawInput} busy={busy} onChange={setRawInput} onSubmit={startSession} />
      )}

      {screen.kind === "result" && <ResultPanel view={screen.result} busy={busy} onBack={backToQuestions} />}

      {"session" in screen && (
        <>
          <p className="progress">{formatProgress(screen.session.progress)}</p>
          {screen.session.result_stale && <p className="hint">{STALE_HINT}</p>}

          {question ? (
            <QuestionCard key={question.question_id} question={question} busy={busy} onAnswer={answer} />
          ) : screen.kind === "generating" ? (
            <p className="card">결과를 만드는 중이에요…</p>
          ) : screen.kind === "completed" ? (
            <p className="card">더 물어볼 것이 없어요. 결과는 지금 답과 맞아요.</p>
          ) : (
            <p className="card">필요한 정보가 모였어요. 결과를 만들어 볼까요?</p>
          )}

          <SummaryList items={screen.session.summary} />

          {actions && (
            <>
              <ActionButton
                action={actions.primary}
                className="primary"
                state={{ busy, canGenerate: screen.session.can_generate }}
                onAct={act}
              />
              {secondary && (
                <ActionButton
                  action={secondary}
                  className="ghost"
                  state={{ busy, canGenerate: screen.session.can_generate }}
                  onAct={act}
                />
              )}
            </>
          )}
        </>
      )}
    </AppShell>
  );
}
