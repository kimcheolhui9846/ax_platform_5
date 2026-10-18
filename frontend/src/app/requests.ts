import { BACKEND_UNREACHABLE, toOutcome } from "../api/client";
import type { ApiResult } from "../api/client";
import { getAsset, getEvidence, getResult, getSession, getTaskForm, getVersion, listSessions, listTasks, previewContext } from "../api/coaching";
import { carryKey } from "../lib/carry";
import { loadKey } from "./load";
import type { Load } from "./load";
import type { Route } from "../lib/routes";
import type { Action } from "./state";

/** 요청 하나. done은 성공한 응답을 상태 변경(Action)으로 바꾼다. */
export type Call<T> = {
  request: () => Promise<ApiResult<T>>;
  done: (data: T, seq: number) => Action;
  load: string | null; // 화면을 그리려고 부르는 요청이면 그 이름(loadKey). 실패하면 같은 화면에서 다시 부르지 않는다
  generating: boolean; // 초안 생성 요청이면 true(생성 중 화면)
  failedRoute: Route | null; // 실패하면 옮길 주소(생성 실패 화면)
  outdatesSessionOnFail: boolean; // 실패해도 서버 세션이 바뀌었을 수 있으면(생성 실패 → FAILED) true
};

export type Runner = <T>(call: Call<T>) => Promise<void>;

/** 요청마다 번호를 붙여 시작과 끝을 알린다. 번호가 다른(늦게 온) 응답은 리듀서가 버린다. */
export function createRunner(dispatch: (action: Action) => void): Runner {
  let seq = 0;
  return async <T>({ request, done, load, generating, failedRoute, outdatesSessionOnFail }: Call<T>) => {
    seq += 1;
    const mine = seq;
    dispatch({ type: "requested", seq: mine, load, generating });
    try {
      const outcome = toOutcome(await request());
      dispatch(
        outcome.ok
          ? done(outcome.data, mine)
          : { type: "failed", seq: mine, message: outcome.message, outdatesSession: outdatesSessionOnFail, next: failedRoute },
      );
    } catch {
      dispatch({ type: "failed", seq: mine, message: BACKEND_UNREACHABLE, outdatesSession: false, next: failedRoute });
    }
  };
}

/** 화면을 그리는 요청도, 생성도 아닌 보통 요청의 기본값. 생성만 덮어쓴다. */
export const PLAIN = { load: null, generating: false, failedRoute: null, outdatesSessionOnFail: false } as const;

/** 화면에 모자란 데이터(needsLoad)를 부른다. */
export function startLoad(run: Runner, load: Load): Promise<void> {
  const key = loadKey(load);
  switch (load.kind) {
    case "tasks":
      return run({
        request: listTasks,
        done: (tasks, seq) => ({ type: "tasksLoaded", seq, tasks }),
        ...PLAIN,
        load: key,
      });
    case "sessions":
      return run({
        request: listSessions,
        done: (sessions, seq) => ({ type: "sessionsLoaded", seq, sessions }),
        ...PLAIN,
        load: key,
      });
    case "form":
      return run({
        request: () => getTaskForm(load.task),
        done: (form, seq) => ({ type: "formLoaded", seq, form }),
        ...PLAIN,
        load: key,
      });
    case "carry":
      return run({
        request: () => previewContext(load.task, load.from.sessionId, load.from.version),
        done: (context, seq) => ({ type: "carryLoaded", seq, task: load.task, key: carryKey(load.task, load.from), context }),
        ...PLAIN,
        load: key,
      });
    case "session":
      return run({
        request: () => getSession(load.sessionId),
        done: (session, seq) => ({ type: "sessionLoaded", seq, session, next: null, noticeConsumed: null, notice: null }),
        ...PLAIN,
        load: key,
      });
    case "result":
      return run({
        request: () => getResult(load.sessionId),
        done: (result, seq) => ({ type: "resultLoaded", seq, result, next: null, outdatesSession: false, notice: null }),
        ...PLAIN,
        load: key,
      });
    case "evidence":
      return run({
        request: () => getEvidence(load.sessionId),
        done: (items, seq) => ({ type: "evidenceLoaded", seq, sessionId: load.sessionId, items }),
        ...PLAIN,
        load: key,
      });
    case "version":
      return run({
        request: () => getVersion(load.sessionId, load.version),
        done: (version, seq) => ({ type: "versionLoaded", seq, version }),
        ...PLAIN,
        load: key,
      });
  }
}

/** 결과 이미지 하나를 data URL로. 화면 불러오기와 따로라 버튼을 막지 않고, 실패하면 null(알림 없이 대체 글을 보인다). */
export async function loadAsset(assetId: string): Promise<string | null> {
  try {
    const outcome = toOutcome(await getAsset(assetId));
    return outcome.ok && typeof outcome.data === "string" ? outcome.data : null;
  } catch {
    return null;
  }
}
