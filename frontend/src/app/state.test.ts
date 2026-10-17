import { describe, expect, it } from "vitest";

import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import type { EvidenceItem } from "../api/types";
import { makeForm, makeResult, makeSession, makeSessionSummary, makeTask, makeVersionView } from "../testing/factories";
import { initialState, isBusy, reducer } from "./state";
import type { AppState } from "./state";

const question: Route = { name: "question", sessionId: "sess_1" };
const confirm: Route = { name: "confirm", sessionId: "sess_1" };
const result: Route = { name: "result", sessionId: "sess_1" };

function waiting(state: AppState, seq: number, load: string | null = null): AppState {
  return reducer(state, { type: "requested", seq, load });
}

describe("reducer", () => {
  it("같은 주소로 옮기면 상태가 그대로다", () => {
    const state = initialState(HOME);
    expect(reducer(state, { type: "navigated", route: { name: "home" } })).toBe(state);
  });

  it("버튼 요청을 시작하면 처리 중이고 이전 알림은 지운다", () => {
    const state = waiting({ ...initialState(HOME), toast: "이전 알림" }, 1);
    expect(isBusy(state)).toBe(true);
    expect(state.toast).toBeNull();
  });

  // 생성 실패 알림 바로 뒤에 세션을 다시 불러오므로, 불러오기가 알림을 지우면 알림이 한순간에 사라진다
  it("불러오기를 시작해도 알림은 지우지 않는다", () => {
    const state = waiting({ ...initialState(HOME), toast: "결과를 만들지 못했습니다." }, 1, "session:sess_1");
    expect(isBusy(state)).toBe(true);
    expect(state.toast).toBe("결과를 만들지 못했습니다.");
  });

  it("기다리는 요청의 응답만 받는다", () => {
    const session = makeSession();
    const state = waiting(initialState(question), 2);
    expect(reducer(state, { type: "sessionLoaded", seq: 1, session, next: null, notice: null })).toBe(state);

    const done = reducer(state, { type: "sessionLoaded", seq: 2, session, next: null, notice: null });
    expect(done.session).toBe(session);
    expect(isBusy(done)).toBe(false);
  });

  it("세션 묶음을 떠나면 기다리던 응답을 버린다", () => {
    const left = reducer(waiting(initialState(question), 1), { type: "navigated", route: HOME });
    expect(isBusy(left)).toBe(false);
    expect(reducer(left, { type: "sessionLoaded", seq: 1, session: makeSession(), next: question, notice: null })).toBe(left);
  });

  it("같은 세션 안에서 옮기면 기다리던 응답을 받는다", () => {
    const moved = reducer(waiting(initialState(question), 1), { type: "navigated", route: confirm });
    expect(isBusy(moved)).toBe(true);

    const done = reducer(moved, { type: "sessionLoaded", seq: 1, session: makeSession(), next: null, notice: null });
    expect(done.route).toEqual(confirm);
    expect(done.session?.session_id).toBe("sess_1");
  });

  it("응답이 다음 화면을 정한다", () => {
    const mode: Route = { name: "mode", task: "product_planning" };
    const done = reducer(waiting(initialState(mode), 1), { type: "sessionLoaded", seq: 1, session: makeSession(), next: question, notice: null });
    expect(done.route).toEqual(question);
  });

  it("알림이 있는 세션 응답은 알림을 띄운다", () => {
    const done = reducer(waiting(initialState(result), 1), {
      type: "sessionLoaded",
      seq: 1,
      session: makeSession({ next_question: null }),
      next: null,
      notice: "더 물어볼 질문이 없어요.",
    });
    expect(done.toast).toBe("더 물어볼 질문이 없어요.");
    expect(done.route).toEqual(result);
  });

  it("불러오기가 실패하면 알림을 띄우고 같은 화면에서 다시 부르지 않게 표시한다", () => {
    const failed = reducer(waiting(initialState(question), 1, "session:sess_1"), {
      type: "failed",
      seq: 1,
      message: "세션을 찾을 수 없습니다.",
      outdatesSession: false,
    });
    expect(failed.toast).toBe("세션을 찾을 수 없습니다.");
    expect(failed.stalled).toBe("session:sess_1");
    expect(reducer(failed, { type: "navigated", route: HOME }).stalled).toBeNull();
  });

  it("다시 시도하면 실패한 불러오기 표시를 지운다", () => {
    const stalled: AppState = { ...initialState(HOME), stalled: "tasks" };
    expect(reducer(stalled, { type: "retried" }).stalled).toBeNull();
  });

  it("버튼 요청이 실패하면 불러오기 실패로 표시하지 않는다", () => {
    const failed = reducer(waiting(initialState(question), 1), { type: "failed", seq: 1, message: "x", outdatesSession: false });
    expect(failed.stalled).toBeNull();
  });

  it("결과를 만들거나 생성이 실패하면 세션을 다시 받게 한다", () => {
    const base: AppState = { ...initialState(confirm), session: makeSession() };
    const made = reducer(waiting(base, 1), { type: "resultLoaded", seq: 1, result: makeResult(), next: result, outdatesSession: true, notice: null });
    expect(made.sessionOutdated).toBe(true);
    expect(made.route).toEqual(result);

    const failed = reducer(waiting(base, 2), { type: "failed", seq: 2, message: "결과를 만들지 못했습니다.", outdatesSession: true });
    expect(failed.sessionOutdated).toBe(true);

    const fresh = reducer(waiting(made, 3), {
      type: "sessionLoaded",
      seq: 3,
      session: makeSession({ next_question: null, has_result: true }),
      next: null,
      notice: null,
    });
    expect(fresh.sessionOutdated).toBe(false);
    expect(fresh.result).not.toBeNull();
  });

  it("결과가 없는 세션을 받으면 남은 결과를 버린다", () => {
    const state: AppState = { ...initialState(question), result: makeResult() };
    const done = reducer(waiting(state, 1), { type: "sessionLoaded", seq: 1, session: makeSession({ has_result: false }), next: null, notice: null });
    expect(done.result).toBeNull();
  });

  it("다른 세션으로 옮기면 그 세션·결과·양식을 비운다", () => {
    const state: AppState = { ...initialState(question), session: makeSession(), result: makeResult(), form: makeForm() };
    const other = reducer(state, { type: "navigated", route: { name: "question", sessionId: "sess_2" } });
    expect([other.session, other.result, other.form]).toEqual([null, null, null]);
  });

  it("같은 과제 안에서는 양식을 그대로 둔다", () => {
    const state: AppState = { ...initialState({ name: "request", task: "product_planning" }), form: makeForm() };
    expect(reducer(state, { type: "navigated", route: { name: "mode", task: "product_planning" } }).form).not.toBeNull();
    expect(reducer(state, { type: "navigated", route: { name: "mode", task: "branding" } }).form).toBeNull();
  });

  it("과제 목록·양식을 받는다", () => {
    const tasks = [makeTask()];
    const listed = reducer(waiting(initialState(HOME), 1, "tasks"), { type: "tasksLoaded", seq: 1, tasks });
    expect(listed.tasks).toBe(tasks);
    const form = makeForm();
    const formed = reducer(waiting(listed, 2, "form:product_planning"), { type: "formLoaded", seq: 2, form });
    expect(formed.form).toBe(form);
  });

  it("쓰다 만 요청 글을 과제별로 두고, 알림을 띄우고 닫는다", () => {
    const drafted = reducer(initialState(HOME), { type: "draftChanged", task: "branding", text: "한글 파우치" });
    expect(drafted.drafts).toEqual({ branding: "한글 파우치" });
    const noticed = reducer(drafted, { type: "noticed", message: "알림" });
    expect(noticed.toast).toBe("알림");
    expect(reducer(noticed, { type: "toastClosed" }).toast).toBeNull();
  });

  it("목록 화면에 새로 들어오면 내 세션 목록을 다시 받고, 목록 화면끼리는 그대로 둔다", () => {
    const sessions = [makeSessionSummary()];
    const onQuestion: AppState = { ...initialState(question), sessions };
    expect(reducer(onQuestion, { type: "navigated", route: HOME }).sessions).toBeNull();
    const onHome: AppState = { ...initialState(HOME), sessions };
    expect(reducer(onHome, { type: "navigated", route: { name: "work" } }).sessions).toBe(sessions);
  });

  it("목록과 버전을 받는다", () => {
    const sessions = [makeSessionSummary()];
    const listed = reducer(waiting(initialState(HOME), 1, "sessions"), { type: "sessionsLoaded", seq: 1, sessions });
    expect(listed.sessions).toBe(sessions);
    const version = makeVersionView();
    const route: Route = { name: "version", sessionId: "sess_1", version: 1 };
    const opened = reducer(waiting(initialState(route), 2, "version:sess_1:1"), { type: "versionLoaded", seq: 2, version });
    expect(opened.version).toBe(version);
  });

  it("버전을 저장하면 저장 완료로 가고, 지금 결과는 다시 받는다", () => {
    const state: AppState = { ...initialState(result), session: makeSession({ has_result: true }), result: makeResult() };
    const version = makeVersionView({ version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true } });
    const saved: Route = { name: "saved", sessionId: "sess_1", version: 1 };
    const done = reducer(waiting(state, 1), { type: "versionSaved", seq: 1, version, next: saved });
    expect(done.route).toEqual(saved);
    expect(done.version).toBe(version);
    expect(done.result).toBeNull();
    // 저장 완료에서 같은 번호의 버전 보기로 옮겨도 받은 버전을 그대로 쓴다
    expect(reducer(done, { type: "navigated", route: { name: "version", sessionId: "sess_1", version: 1 } }).version).toBe(version);
  });

  it("다른 버전으로 옮기면 보던 버전을 비운다", () => {
    const version = makeVersionView();
    const state: AppState = { ...initialState({ name: "version", sessionId: "sess_1", version: 1 }), version };
    expect(reducer(state, { type: "navigated", route: { name: "version", sessionId: "sess_1", version: 2 } }).version).toBeNull();
    expect(reducer(state, { type: "navigated", route: result }).version).toBeNull();
  });
});

describe("reducer — 알림이 있는 결과", () => {
  it("알림이 있는 결과 응답은 알림을 띄운다", () => {
    const route: Route = { name: "edit", sessionId: "sess_1", order: 1 };
    const next = reducer(waiting(initialState(route), 1), {
      type: "resultLoaded",
      seq: 1,
      result: makeResult({ session_id: "sess_1" }),
      next: { name: "result", sessionId: "sess_1" },
      outdatesSession: false,
      notice: "문구를 반영했어요.",
    });
    expect(next.toast).toBe("문구를 반영했어요.");
    expect(next.route).toEqual({ name: "result", sessionId: "sess_1" });
  });
});

describe("reducer — 근거·이미지", () => {
  const items = [{ source_id: "zip" }] as unknown as EvidenceItem[];

  it("기다리던 요청의 근거 자료만 받는다", () => {
    const state = waiting(initialState(result), 2);
    expect(reducer(state, { type: "evidenceLoaded", seq: 1, sessionId: "sess_1", items }).evidence).toBeNull();
    const done = reducer(state, { type: "evidenceLoaded", seq: 2, sessionId: "sess_1", items });
    expect(done.evidence).toEqual({ sessionId: "sess_1", items });
    expect(isBusy(done)).toBe(false);
  });

  it("이미지는 요청 번호 없이 id로 가려 받는다(불러오는 중은 null, 실패도 null)", () => {
    const requested = reducer(initialState(result), { type: "assetRequested", assetId: "a" });
    expect(requested.assets).toEqual({ a: null });
    const loaded = reducer(requested, { type: "assetLoaded", assetId: "a", url: "data:image/png;base64,AA" });
    expect(loaded.assets).toEqual({ a: "data:image/png;base64,AA" });
    expect(reducer(requested, { type: "assetLoaded", assetId: "a", url: null }).assets).toEqual({ a: null });
  });

  it("요청하지 않았거나 세션을 떠나 비워진 뒤 온 이미지는 버린다", () => {
    const state = initialState(result);
    expect(reducer(state, { type: "assetLoaded", assetId: "a", url: "data:x" })).toBe(state);
  });

  it("다른 세션으로 가면 이미지와 근거 자료를 비우고, 같은 세션 안에서는 둔다", () => {
    const session = makeSession({ session_id: "sess_1" });
    const base: AppState = { ...initialState(result), session, assets: { a: "data:x" }, evidence: { sessionId: "sess_1", items } };
    const same = reducer(base, { type: "navigated", route: { name: "evidence", sessionId: "sess_1" } });
    expect(same.assets).toEqual({ a: "data:x" });
    expect(same.evidence).toEqual({ sessionId: "sess_1", items });
    const other = reducer(base, { type: "navigated", route: { name: "result", sessionId: "sess_2" } });
    expect(other.assets).toEqual({});
    expect(other.evidence).toBeNull();
  });

  it("결과를 받아도 근거 자료는 건드리지 않는다", () => {
    const base: AppState = { ...waiting(initialState(result), 1), evidence: { sessionId: "sess_1", items } };
    const next = reducer(base, {
      type: "resultLoaded",
      seq: 1,
      result: makeResult({ session_id: "sess_1" }),
      next: null,
      outdatesSession: false,
      notice: null,
    });
    expect(next.evidence).toEqual({ sessionId: "sess_1", items });
  });
});
