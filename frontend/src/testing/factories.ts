// 테스트에서 쓰는 API 값. 생성된 타입을 쓰므로 계약이 바뀌면 여기서 먼저 깨진다.
import type {
  FlowItem,
  Question,
  ResultView,
  SessionSummary,
  SessionView,
  TaskForm,
  TaskSummary,
  VersionView,
} from "../api/types";

export function makeQuestion(overrides: Partial<Question> = {}): Question {
  return {
    question_id: "q_1",
    field: "user",
    text: "이 상품을 주로 쓰는 사람은 누구인가요?",
    options: [
      { id: "o1", label: "20~30대 1인 가구", ai_suggested: false },
      { id: "o2", label: "선물을 사는 사람", ai_suggested: false },
    ],
    multi_select: false,
    level: 0,
    is_ai_proposal: false,
    ...overrides,
  };
}

export function makeFlowItem(overrides: Partial<FlowItem> = {}): FlowItem {
  return {
    field: "user",
    label: "사용자",
    text: "이 상품을 주로 쓰는 사람은 누구인가요?",
    status: "upcoming",
    answer: null,
    question: null,
    ...overrides,
  };
}

export function makeTask(overrides: Partial<TaskSummary> = {}): TaskSummary {
  return {
    task_type: "product_planning",
    title: "상품기획",
    description: "사용 장면과 핵심 기능, 제작 방향을 정리해요.",
    heading: "만들고 싶은 상품을 구체화하고 싶어요",
    deliverable: "상품 콘셉트 · 첫 제작 기획서",
    evidence_sources: 0,
    ...overrides,
  };
}

export function makeForm(overrides: Partial<TaskForm> = {}): TaskForm {
  return {
    task_type: "product_planning",
    title: "상품기획",
    description: "사용 장면과 핵심 기능, 제작 방향을 정리해요.",
    input_placeholder: "예) 집들이 선물용 수제 향초",
    input_examples: ["집들이 선물용 수제 향초"],
    modes: [
      { mode: "quick", question_cap: 3 },
      { mode: "standard", question_cap: 5 },
      { mode: "precise", question_cap: 10 },
    ],
    fields: [],
    ...overrides,
  };
}

/** 기본은 첫 질문이 걸린 세션이다. next_question을 null로 주면 흐름도 비운다. */
export function makeSession(overrides: Partial<SessionView> = {}): SessionView {
  const question = overrides.next_question === undefined ? makeQuestion() : overrides.next_question;
  return {
    session_id: "sess_1",
    task_type: "product_planning",
    mode: "standard",
    status: question ? "clarifying" : "confirming",
    raw_input: "수제 향초",
    next_question: question,
    progress: { asked: 0, cap: 5, readiness: 0.3 },
    summary: [
      {
        field: "product_idea",
        label: "상품 아이디어",
        value: "수제 향초",
        source: "user_free_text",
        source_label: "직접 입력",
        confidence: 1,
        is_assumption: false,
      },
    ],
    unknowns: [],
    supplements: [],
    supplements_changed: false,
    flow: question
      ? [makeFlowItem({ field: question.field, text: question.text, status: "current", question })]
      : [],
    can_generate: true,
    has_result: false,
    result_stale: false,
    error: null,
    ...overrides,
  };
}

export function makeResult(overrides: Partial<ResultView> = {}): ResultView {
  return {
    session_id: "sess_1",
    status: "completed",
    stale: false,
    version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: false },
    summary: [
      {
        field: "product_idea",
        label: "상품 아이디어",
        value: "수제 향초",
        source: "user_free_text",
        source_label: "직접 입력",
        confidence: 1,
        is_assumption: false,
      },
    ],
    unknowns: [],
    supplements: [],
    validation: { issues: [], passed: true },
    result: {
      sections: [{ order: 1, heading: "상품 콘셉트", kind: "diagnosis", blocks: [{ type: "text", text: "집들이 선물용 수제 향초." }] }],
      assumptions: [],
      evidence: [],
      full_text: "상품 콘셉트",
      content: {},
      generated_at: "2026-10-16T09:00:00Z",
    },
    ...overrides,
  };
}

export function makeSessionSummary(overrides: Partial<SessionSummary> = {}): SessionSummary {
  return {
    session_id: "sess_1",
    task_type: "product_planning",
    title: "상품기획",
    raw_input: "수제 향초",
    mode: "standard",
    has_question: true,
    has_result: false,
    result_stale: false,
    latest_version: null,
    saved_versions: [],
    updated_at: "2026-10-16T09:00:00Z",
    ...overrides,
  };
}

export function makeVersionView(overrides: Partial<VersionView> = {}): VersionView {
  const result = makeResult();
  return {
    session_id: "sess_1",
    version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: false },
    latest: true,
    result: result.result,
    validation: result.validation,
    summary: result.summary,
    unknowns: [],
    supplements: [],
    ...overrides,
  };
}
