import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/coaching", () => ({
  listTasks: vi.fn(),
  getTaskForm: vi.fn(),
  getSession: vi.fn(),
  getResult: vi.fn(),
  listSessions: vi.fn(),
  getVersion: vi.fn(),
  getAsset: vi.fn(),
}));

import { BACKEND_UNREACHABLE } from "../api/client";
import { getAsset, getResult, getSession, getTaskForm, getVersion, listSessions, listTasks } from "../api/coaching";
import { makeForm, makeResult, makeSession, makeSessionSummary, makeTask, makeVersionView } from "../testing/factories";
import { createRunner, loadAsset, startLoad } from "./requests";
import type { Call, Runner } from "./requests";
import type { Action } from "./state";

beforeEach(() => vi.clearAllMocks());

const ok = <T>(data: T) => ({ data, response: new Response(null, { status: 200 }) });
const jsonHeaders = { "content-type": "application/json" };

describe("createRunner", () => {
  it("생성 요청이면 requested에 generating을 싣는다", async () => {
    const actions: Action[] = [];
    const run = createRunner((action) => actions.push(action));
    const session = makeSession();
    await run({
      request: async () => ok(session),
      done: (data, seq) => ({ type: "sessionLoaded", seq, session: data, next: null, noticeConsumed: null, notice: null }),
      load: null,
      generating: true,
      failedRoute: null,
      outdatesSessionOnFail: true,
    });
    expect(actions[0]).toEqual({ type: "requested", seq: 1, load: null, generating: true });
  });

  it("요청마다 번호를 붙여 시작과 성공을 알린다", async () => {
    const actions: Action[] = [];
    const run = createRunner((action) => actions.push(action));
    const session = makeSession();
    const call: Call<typeof session> = {
      request: async () => ok(session),
      done: (data, seq) => ({ type: "sessionLoaded", seq, session: data, next: null, noticeConsumed: null, notice: null }),
      load: "session:sess_1",
      generating: false,
      failedRoute: null,
      outdatesSessionOnFail: false,
    };

    await run(call);
    await run({ ...call, load: null });

    expect(actions).toEqual([
      { type: "requested", seq: 1, load: "session:sess_1", generating: false },
      { type: "sessionLoaded", seq: 1, session, next: null, noticeConsumed: null, notice: null },
      { type: "requested", seq: 2, load: null, generating: false },
      { type: "sessionLoaded", seq: 2, session, next: null, noticeConsumed: null, notice: null },
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
      generating: false,
      failedRoute: { name: "failed", sessionId: "sess_1" },
      outdatesSessionOnFail: true,
    });
    expect(actions[1]).toEqual({
      type: "failed",
      seq: 1,
      message: "결과를 만들지 못했습니다.",
      outdatesSession: true,
      next: { name: "failed", sessionId: "sess_1" },
    });
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
      generating: false,
      failedRoute: { name: "failed", sessionId: "sess_1" },
      outdatesSessionOnFail: true,
    });
    expect(actions[1]).toEqual({
      type: "failed",
      seq: 1,
      message: BACKEND_UNREACHABLE,
      outdatesSession: false,
      next: { name: "failed", sessionId: "sess_1" },
    });
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
    expect(calls.every((c) => !c.outdatesSessionOnFail && !c.generating)).toBe(true);

    for (const call of calls) await call.request();
    expect(listTasks).toHaveBeenCalled();
    expect(getTaskForm).toHaveBeenCalledWith("branding");
    expect(getSession).toHaveBeenCalledWith("sess_1");
    expect(getResult).toHaveBeenCalledWith("sess_1");

    const [tasks, form, session, result] = calls;
    expect(tasks.done([makeTask()], 1)).toEqual({ type: "tasksLoaded", seq: 1, tasks: [makeTask()] });
    expect(form.done(makeForm(), 2)).toEqual({ type: "formLoaded", seq: 2, form: makeForm() });
    expect(session.done(makeSession(), 3)).toEqual({ type: "sessionLoaded", seq: 3, session: makeSession(), next: null, noticeConsumed: null, notice: null });
    expect(result.done(makeResult(), 4)).toEqual({ type: "resultLoaded", seq: 4, result: makeResult(), next: null, outdatesSession: false, notice: null });
  });

  it("내 세션 목록과 버전을 부른다", async () => {
    const { run, calls } = capture();
    await startLoad(run, { kind: "sessions" });
    await startLoad(run, { kind: "version", sessionId: "sess_1", version: 2 });

    expect(calls.map((c) => c.load)).toEqual(["sessions", "version:sess_1:2"]);
    for (const call of calls) await call.request();
    expect(listSessions).toHaveBeenCalled();
    expect(getVersion).toHaveBeenCalledWith("sess_1", 2);

    const [sessions, version] = calls;
    expect(sessions.done([makeSessionSummary()], 1)).toEqual({ type: "sessionsLoaded", seq: 1, sessions: [makeSessionSummary()] });
    expect(version.done(makeVersionView(), 2)).toEqual({ type: "versionLoaded", seq: 2, version: makeVersionView() });
  });
});

describe("loadAsset", () => {
  it("받은 이미지는 data URL로 돌려준다", async () => {
    vi.mocked(getAsset).mockResolvedValue(ok("data:image/svg+xml;base64,AA"));
    expect(await loadAsset("a")).toBe("data:image/svg+xml;base64,AA");
  });

  it("실패 응답이면 null이다", async () => {
    vi.mocked(getAsset).mockResolvedValue({
      data: undefined,
      error: { detail: "없어요" },
      response: new Response(null, { status: 404, headers: jsonHeaders }),
    });
    expect(await loadAsset("a")).toBeNull();
  });

  it("성공 응답이어도 이미지가 아니라 data가 없으면 null이다", async () => {
    vi.mocked(getAsset).mockResolvedValue({ data: undefined, response: new Response(null, { status: 200 }) });
    expect(await loadAsset("a")).toBeNull();
  });

  it("예외가 나면 null이다", async () => {
    vi.mocked(getAsset).mockRejectedValue(new TypeError("Failed to fetch"));
    expect(await loadAsset("a")).toBeNull();
  });
});
