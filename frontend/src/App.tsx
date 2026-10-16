import { useEffect, useState } from "react";

import { errorMessage } from "./api/client";
import { createSession, generateResult, listTasks, submitAnswer } from "./api/coaching";
import type { ApiResult } from "./api/coaching";
import type { AnswerBody, ResultView, SessionView, TaskSummary } from "./api/types";
import { IdeaForm } from "./components/IdeaForm";
import { QuestionCard } from "./components/QuestionCard";
import { ResultPanel } from "./components/ResultPanel";
import { SummaryList } from "./components/SummaryList";
import { TaskPicker } from "./components/TaskPicker";
import { formatProgress } from "./lib/progress";

/** 화면 상태(과제, 세션, 결과)와 요청 상태(busy/error)는 이 컴포넌트에서만 바꾼다. */
export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [task, setTask] = useState<TaskSummary | null>(null);
  const [rawInput, setRawInput] = useState("");
  const [session, setSession] = useState<SessionView | null>(null);
  const [result, setResult] = useState<ResultView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run<T>(request: () => Promise<ApiResult<T>>, onData: (data: T) => void) {
    setBusy(true);
    setError(null);
    try {
      const { data, error } = await request();
      if (data !== undefined) onData(data);
      else setError(errorMessage(error));
    } catch {
      setError("서버에 연결하지 못했습니다. 백엔드가 켜져 있는지 확인해 주세요.");
    } finally {
      setBusy(false);
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
    void run(() => generateResult(session_id), setResult);
  }

  function reset() {
    setTask(null);
    setRawInput("");
    setSession(null);
    setResult(null);
    setError(null);
  }

  return (
    <main>
      <header>
        <h1>AX 코칭</h1>
        {task && (
          <button type="button" className="ghost" disabled={busy} onClick={reset}>
            처음으로
          </button>
        )}
      </header>

      {error && <p className="error">{error}</p>}

      {!task && <TaskPicker tasks={tasks} onPick={setTask} />}

      {task && !session && (
        <IdeaForm title={task.title} value={rawInput} busy={busy} onChange={setRawInput} onSubmit={startSession} />
      )}

      {session && !result && (
        <>
          <p className="progress">{formatProgress(session.progress)}</p>

          {session.next_question ? (
            <QuestionCard question={session.next_question} busy={busy} onAnswer={answer} />
          ) : (
            <p className="card">필요한 정보가 모였어요. 결과를 만들어 볼까요?</p>
          )}

          <SummaryList items={session.summary} />

          <button type="button" className="primary" disabled={busy || !session.can_generate} onClick={generate}>
            {busy ? "처리 중…" : "이대로 결과 만들기"}
          </button>
        </>
      )}

      {result && <ResultPanel view={result} />}
    </main>
  );
}
