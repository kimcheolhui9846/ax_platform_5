import { BACKEND_UNREACHABLE, toOutcome } from "../api/client";
import type { ApiResult } from "../api/client";
import { getResult, getSession, getTaskForm, getVersion, listSessions, listTasks } from "../api/coaching";
import { loadKey } from "./load";
import type { Load } from "./load";
import type { Action } from "./state";

/** 요청 하나. done은 성공한 응답을 상태 변경(Action)으로 바꾼다. */
export type Call<T> = {
  request: () => Promise<ApiResult<T>>;
  done: (data: T, seq: number) => Action;
  load: string | null; // 화면을 그리려고 부르는 요청이면 그 이름(loadKey). 실패하면 같은 화면에서 다시 부르지 않는다
  outdatesSessionOnFail: boolean; // 실패해도 서버 세션이 바뀌었을 수 있으면(생성 실패 → FAILED) true
};

export type Runner = <T>(call: Call<T>) => Promise<void>;

/** 요청마다 번호를 붙여 시작과 끝을 알린다. 번호가 다른(늦게 온) 응답은 리듀서가 버린다. */
export function createRunner(dispatch: (action: Action) => void): Runner {
  let seq = 0;
  return async <T>({ request, done, load, outdatesSessionOnFail }: Call<T>) => {
    seq += 1;
    const mine = seq;
    dispatch({ type: "requested", seq: mine, load });
    try {
      const outcome = toOutcome(await request());
      dispatch(
        outcome.ok
          ? done(outcome.data, mine)
          : { type: "failed", seq: mine, message: outcome.message, outdatesSession: outdatesSessionOnFail },
      );
    } catch {
      dispatch({ type: "failed", seq: mine, message: BACKEND_UNREACHABLE, outdatesSession: false });
    }
  };
}

/** 화면에 모자란 데이터(needsLoad)를 부른다. */
export function startLoad(run: Runner, load: Load): Promise<void> {
  const key = loadKey(load);
  switch (load.kind) {
    case "tasks":
      return run({
        request: listTasks,
        done: (tasks, seq) => ({ type: "tasksLoaded", seq, tasks }),
        load: key,
        outdatesSessionOnFail: false,
      });
    case "sessions":
      return run({
        request: listSessions,
        done: (sessions, seq) => ({ type: "sessionsLoaded", seq, sessions }),
        load: key,
        outdatesSessionOnFail: false,
      });
    case "form":
      return run({
        request: () => getTaskForm(load.task),
        done: (form, seq) => ({ type: "formLoaded", seq, form }),
        load: key,
        outdatesSessionOnFail: false,
      });
    case "session":
      return run({
        request: () => getSession(load.sessionId),
        done: (session, seq) => ({ type: "sessionLoaded", seq, session, next: null, notice: null }),
        load: key,
        outdatesSessionOnFail: false,
      });
    case "result":
      return run({
        request: () => getResult(load.sessionId),
        done: (result, seq) => ({ type: "resultLoaded", seq, result, next: null, outdatesSession: false }),
        load: key,
        outdatesSessionOnFail: false,
      });
    case "version":
      return run({
        request: () => getVersion(load.sessionId, load.version),
        done: (version, seq) => ({ type: "versionLoaded", seq, version }),
        load: key,
        outdatesSessionOnFail: false,
      });
  }
}
