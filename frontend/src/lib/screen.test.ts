import { describe, expect, it } from "vitest";

import type { Question, ResultView, SessionView, TaskSummary } from "../api/types";
import { STALE_HINT, screenOf } from "./screen";

const task: TaskSummary = { task_type: "branding", title: "브랜딩", description: "" };

const question: Question = {
  question_id: "q_1",
  field: "customer",
  text: "누구에게 파나요?",
  options: [],
  multi_select: false,
  level: 0,
  is_ai_proposal: false,
};

function session(overrides: Partial<SessionView> = {}): SessionView {
  return {
    session_id: "sess_1",
    task_type: "branding",
    mode: "standard",
    status: "clarifying",
    next_question: question,
    progress: { asked: 0, cap: 5, readiness: 0.3 },
    summary: [],
    unknowns: [],
    can_generate: true,
    result_stale: false,
    error: null,
    ...overrides,
  };
}

const result = { session_id: "sess_1", status: "completed", stale: false } as ResultView;

describe("screenOf", () => {
  it("과제를 고르기 전에는 과제 선택(초기)", () => {
    expect(screenOf(null, null, null)).toEqual({ kind: "pick_task" });
  });

  it("세션이 없으면 아이디어 입력(초기)", () => {
    expect(screenOf(task, null, null)).toEqual({ kind: "idea", task });
  });

  it("걸린 질문이 있으면 정보 부족", () => {
    const s = session();
    expect(screenOf(task, s, null)).toEqual({ kind: "clarifying", session: s, question });
  });

  it("질문이 없고 결과가 최신이면 생성 대기", () => {
    const s = session({ status: "confirming", next_question: null });
    expect(screenOf(task, s, null)).toEqual({ kind: "ready", session: s });
  });

  it("질문이 없고 결과가 최신이 아니면 수정", () => {
    const s = session({ status: "revising", next_question: null, result_stale: true });
    expect(screenOf(task, s, null)).toEqual({ kind: "revising", session: s });
  });

  it("생성 중 상태는 생성 중", () => {
    const s = session({ status: "generating", next_question: null });
    expect(screenOf(task, s, null)).toEqual({ kind: "generating", session: s });
  });

  it("실패 상태는 실패이고 남은 질문을 함께 준다", () => {
    const s = session({ status: "failed", error: "결과를 만들지 못했습니다." });
    expect(screenOf(task, s, null)).toEqual({ kind: "failed", session: s, question });
  });

  it("결과가 있으면 완료", () => {
    expect(screenOf(task, session(), result)).toEqual({ kind: "result", result });
  });
});

describe("STALE_HINT", () => {
  it("최신이 아니라는 안내를 담는다", () => {
    expect(STALE_HINT).toContain("결과가 최신이 아님");
  });
});
