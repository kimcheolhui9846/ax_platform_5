import type { Question, ResultView, SessionView, TaskSummary } from "../api/types";

export const TASKS: TaskSummary[] = [
  { task_type: "business_plan", title: "사업계획", description: "사업 가설과 실행 구조를 정리합니다.", heading: "아이디어를 사업으로 시작하고 싶어요", deliverable: "사업 가설 · 실행 계획서" },
  { task_type: "product_planning", title: "상품기획", description: "고객 문제를 해결하는 상품과 MVP를 정의합니다.", heading: "만들고 싶은 상품을 구체화하고 싶어요", deliverable: "상품 콘셉트 · 첫 제작 기획서" },
  { task_type: "branding", title: "브랜딩", description: "차별화된 정체성과 표현 체계를 세웁니다.", heading: "내 브랜드만의 인상을 만들고 싶어요", deliverable: "브랜드 콘셉트 · 표현 가이드" },
  { task_type: "marketing_content", title: "마케팅 콘텐츠", description: "채널과 목적에 맞는 실행 콘텐츠를 만듭니다.", heading: "사람들에게 보여줄 홍보 글이 필요해요", deliverable: "게시글 · 행동 유도 문구" },
];

export const QUESTION: Question = {
  question_id: "q_preview_1",
  field: "usage_context",
  text: "이 파우치는 어떤 순간에 쓰이면 좋을까요?",
  options: [
    { id: "o1", label: "가방 안의 작은 물건을 찾기 쉽게", ai_suggested: false },
    { id: "o2", label: "감사의 마음을 담은 작은 선물로", ai_suggested: false },
    { id: "o3", label: "여행 가방을 간단히 정리하도록", ai_suggested: false },
  ],
  multi_select: false,
  level: 0,
  is_ai_proposal: false,
};

export const LADDER_QUESTION: Question = {
  ...QUESTION,
  question_id: "q_preview_2",
  text: "하루 중 이 파우치를 가장 먼저 꺼내는 때는 언제인가요?",
  options: [
    { id: "o1", label: "출근길", ai_suggested: false },
    { id: "o2", label: "점심시간", ai_suggested: false },
  ],
  level: 1,
};

const SESSION_BASE: SessionView = {
  session_id: "sess_preview",
  task_type: "product_planning",
  mode: "standard",
  status: "clarifying",
  raw_input: "한글을 활용한 파우치를 만들고 싶어요",
  flow: [],
  next_question: QUESTION,
  progress: { asked: 1, cap: 5, readiness: 0.38 },
  summary: [
    {
      field: "product_idea",
      label: "상품 아이디어",
      value: "한글을 활용한 파우치",
      source: "user_free_text",
      source_label: "직접 입력",
      confidence: 1,
      is_assumption: false,
    },
    {
      field: "user",
      label: "사용자",
      value: "일상 소지품을 정리하는 사람",
      source: "user_selected_ai_option",
      source_label: "선택",
      confidence: 1,
      is_assumption: false,
    },
  ],
  unknowns: [],
  can_generate: true,
  has_result: false,
  result_stale: false,
  error: null,
};

export const SESSION_CLARIFYING: SessionView = SESSION_BASE;
export const SESSION_LADDER: SessionView = { ...SESSION_BASE, next_question: LADDER_QUESTION };
export const SESSION_READY: SessionView = { ...SESSION_BASE, status: "confirming", next_question: null, progress: { asked: 5, cap: 5, readiness: 0.82 } };

export const RESULT: ResultView = {
  session_id: "sess_preview",
  status: "completed",
  stale: false,
  validation: { issues: [], passed: true },
  result: {
    cards: [
      { card_type: "diagnosis", order: 1, title: "상품 콘셉트", body: "가방 안의 작은 물건을 정리하는 한글 파우치. 한글 형태를 일상 소품으로 즐기게 한다." },
      { card_type: "suggestion", order: 2, title: "첫 제작 기획", body: "수납과 사용 편의를 우선한다. 소재와 봉제 가능성을 먼저 확인한다." },
      { card_type: "action", order: 3, title: "다음 실행", body: "잠재 고객 다섯 명에게 시제품 사진을 보여 주고 구매 이유와 우려를 듣는다." },
    ],
    assumptions: [
      { field: "price", label: "판매 가격", value: "18,000원 / 개", reason: "비슷한 소형 파우치의 가격대", requires_confirmation: true },
    ],
    full_text: "상품 콘셉트\n가방 안의 작은 물건을 정리하는 한글 파우치.",
    content: {},
    generated_at: "2026-10-16T09:00:00Z",
  },
};
