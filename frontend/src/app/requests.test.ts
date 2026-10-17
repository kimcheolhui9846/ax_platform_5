import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/coaching", () => ({
  listTasks: vi.fn(),
  getTaskForm: vi.fn(),
  getSession: vi.fn(),
  getResult: vi.fn(),
}));

import { BACKEND_UNREACHABLE } from "../api/client";
import { getResult, getSession, getTaskForm, listTasks } from "../api/coaching";
import { makeForm, makeResult, makeSession, makeTask } from "../testing/factories";
import { createRunner, startLoad } from "./requests";
import type { Call, Runner } from "./requests";
import type { Action } from "./state";

beforeEach(() => vi.clearAllMocks());

const ok = <T>(data: T) => ({ data, response: new Response(null, { status: 200 }) });
const jsonHeaders = { "content-type": "application/json" };

describe("createRunner", () => {
  it("요청마다 번호를 붙여 시작과 성공을 알린다", async () => {
    const actions: Action[] = [];
    const run = createRunner((action) => actions.push(action));
    const session = makeSession();
    const call: Call<typeof session> = {
      request: async () => ok(session),
      done: (data, seq) => ({ type: "sessionLoaded", seq, session: data, next: null, notice: null }),
      load: "session:sess_1",
      outdatesSessionOnFail: false,
    };

    await run(call);
    await run({ ...call, load: null });

    expect(actions).toEqual([
      { type: "requested", seq: 1, load: "session:sess_1" },
      { type: "sessionLoaded", seq: 1, session, next: null, notice: null },
      { type: "requested", seq: 2, load: null },
      { type: "sessionLoaded", seq: 2, session, next: null, notice: null },
    ]);
  });

  it("실패 응답은 그 문구로, 생성처럼 세션이 바뀌었을 수 있으면 다시 받게 실패한다", async () => {
    const actions: Action[] = [];
    const run = createRunner((action) => actions.push(action));
    await run({
      request: async () => ({
        error: { detail: "결과를 만들지 못했습니다." },
        response: new Response(null, { status: 502, headers: jsonHeaders }),
      }),
      done: () => ({ type: "toastClosed" }),
      load: null,
      outdatesSessionOnFail: true,
    });
    expect(actions[1]).toEqual({ type: "failed", seq: 1, message: "결과를 만들지 못했습니다.", outdatesSession: true });
  });

  it("연결 예외는 백엔드 미연결이다", async () => {
    const actions: Action[] = [];
    const run = createRunner((action) => actions.push(action));
    await run({
      request: async () => {
        throw new TypeError("Failed to fetch");
      },
      done: () => ({ type: "toastClosed" }),
      load: "tasks",
      outdatesSessionOnFail: true,
    });
    expect(actions[1]).toEqual({ type: "failed", seq: 1, message: BACKEND_UNREACHABLE, outdatesSession: false });
  });
});

describe("startLoad", () => {
  function capture(): { run: Runner; calls: Call<unknown>[] } {
    const calls: Call<unknown>[] = [];
    const run: Runner = async <T>(call: Call<T>) => {
      calls.push(call as unknown as Call<unknown>);
    };
    return { run, calls };
  }

  it("불러오기마다 맞는 API와 응답 동작을 쓴다", async () => {
    const { run, calls } = capture();
    await startLoad(run, { kind: "tasks" });
    await startLoad(run, { kind: "form", task: "branding" });
    await startLoad(run, { kind: "session", sessionId: "sess_1" });
    await startLoad(run, { kind: "result", sessionId: "sess_1" });

    expect(calls.map((c) => c.load)).toEqual(["tasks", "form:branding", "session:sess_1", "result:sess_1"]);
    expect(calls.every((c) => !c.outdatesSessionOnFail)).toBe(true);

    for (const call of calls) await call.request();
    expect(listTasks).toHaveBeenCalled();
    expect(getTaskForm).toHaveBeenCalledWith("branding");
    expect(getSession).toHaveBeenCalledWith("sess_1");
    expect(getResult).toHaveBeenCalledWith("sess_1");

    const [tasks, form, session, result] = calls;
    expect(tasks.done([makeTask()], 1)).toEqual({ type: "tasksLoaded", seq: 1, tasks: [makeTask()] });
    expect(form.done(makeForm(), 2)).toEqual({ type: "formLoaded", seq: 2, form: makeForm() });
    expect(session.done(makeSession(), 3)).toEqual({ type: "sessionLoaded", seq: 3, session: makeSession(), next: null, notice: null });
    expect(result.done(makeResult(), 4)).toEqual({ type: "resultLoaded", seq: 4, result: makeResult(), next: null, outdatesSession: false });
  });
});
