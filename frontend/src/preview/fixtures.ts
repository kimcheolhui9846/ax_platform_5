// 미리보기 갤러리의 샘플 값. 생성된 API 타입을 쓰므로 계약이 바뀌면 빌드가 깨져 바로 알 수 있다.
import type { EvidenceItem, FlowItem, Question, ResultView, SessionSummary, SessionView, SummaryItem, SupplementItem, TaskForm, TaskSummary, VersionView } from "../api/types";
import type { EditableFlowItem } from "../lib/flowView";

export const TASKS: TaskSummary[] = [
  {
    task_type: "business_plan",
    title: "사업계획",
    description: "고객과 수익 구조, 첫 실행 계획을 정리해요.",
    heading: "아이디어를 사업으로 시작하고 싶어요",
    deliverable: "사업 가설 · 실행 계획서",
    evidence_sources: 0,
  },
  {
    task_type: "product_planning",
    title: "상품기획",
    description: "사용 장면과 핵심 기능, 제작 방향을 정리해요.",
    heading: "만들고 싶은 상품을 구체화하고 싶어요",
    deliverable: "상품 콘셉트 · 첫 제작 기획서",
    evidence_sources: 2,
  },
  {
    task_type: "branding",
    title: "브랜딩",
    description: "브랜드의 성격과 말투, 표현 방향을 정리해요.",
    heading: "내 브랜드만의 인상을 만들고 싶어요",
    deliverable: "브랜드 콘셉트 · 표현 가이드",
    evidence_sources: 0,
  },
  {
    task_type: "marketing_content",
    title: "마케팅 콘텐츠",
    description: "목적에 맞는 메시지를 실제 문구로 만들어요.",
    heading: "사람들에게 보여줄 홍보 글이 필요해요",
    deliverable: "게시글 · 행동 유도 문구",
    evidence_sources: 0,
  },
];

export const PRODUCT = TASKS[1];

export const REQUEST = "한글을 활용한 파우치를 만들고 싶은데, 어떤 상품으로 만들면 좋을까요?";

export const FORM: TaskForm = {
  task_type: "product_planning",
  title: "상품기획",
  description: PRODUCT.description,
  input_placeholder: "예) 집들이 선물용 수제 향초",
  input_examples: [REQUEST],
  modes: [
    { mode: "quick", question_cap: 3 },
    { mode: "standard", question_cap: 5 },
    { mode: "precise", question_cap: 10 },
  ],
  fields: [],
};

const USER_QUESTION: Question = {
  question_id: "q_user",
  field: "user",
  text: "이 상품을 주로 쓰는 사람은 누구인가요?",
  options: [
    { id: "o1", label: "20~30대 1인 가구", ai_suggested: false },
    { id: "o2", label: "선물을 사는 사람", ai_suggested: false },
    { id: "o3", label: "아이를 키우는 부모", ai_suggested: false },
  ],
  multi_select: false,
  level: 0,
  is_ai_proposal: false,
};

export const QUESTION: Question = {
  question_id: "q_usage",
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
  question_id: "q_usage_1",
  text: "하루 중 이 파우치를 가장 먼저 꺼내는 때는 언제인가요?",
  options: [
    { id: "o1", label: "출근길", ai_suggested: false },
    { id: "o2", label: "점심시간", ai_suggested: false },
    { id: "o3", label: "여행 준비할 때", ai_suggested: false },
  ],
  level: 1,
};

export const PROPOSAL_QUESTION: Question = {
  ...QUESTION,
  question_id: "q_usage_4",
  text: "이 중 가장 가까운 걸 고르거나 고쳐 주세요.",
  options: [
    { id: "p4_1", label: "가방 속 작은 소지품 정리", ai_suggested: true },
    { id: "p4_2", label: "마음을 전하는 작은 선물", ai_suggested: true },
    { id: "p4_3", label: "여행용 정리 파우치", ai_suggested: true },
  ],
  level: 4,
  is_ai_proposal: true,
};

export const ANSWERED_USER: EditableFlowItem = {
  field: "user",
  label: "사용자",
  text: USER_QUESTION.text,
  status: "answered",
  answer: "일상 소지품을 정리하는 사람",
  question: USER_QUESTION,
};

function current(question: Question): FlowItem {
  return { field: "usage_context", label: "사용 상황", text: question.text, status: "current", answer: null, question };
}

const UPCOMING: FlowItem[] = [
  { field: "customer_problem", label: "고객 문제", text: "사용자가 지금 겪는 불편은 무엇인가요?", status: "upcoming", answer: null, question: null },
  { field: "core_value", label: "핵심 가치", text: "이 상품이 다른 상품보다 나은 점 하나는 무엇인가요?", status: "upcoming", answer: null, question: null },
  { field: "mvp", label: "MVP 구성", text: "처음 판매할 때 꼭 들어가야 하는 구성은 무엇인가요?", status: "upcoming", answer: null, question: null },
];

const DONE_FLOW: FlowItem[] = [
  ANSWERED_USER,
  { ...current(QUESTION), status: "answered", answer: "가방 안의 작은 물건을 찾기 쉽게" },
  { ...UPCOMING[0], status: "skipped", question: { ...USER_QUESTION, question_id: "q_problem", field: "customer_problem", text: UPCOMING[0].text, options: [] } },
  { ...UPCOMING[1], status: "answered", answer: "한글 형태를 일상 소품으로 즐긴다", question: { ...USER_QUESTION, question_id: "q_value", field: "core_value", text: UPCOMING[1].text, options: [] } },
];

const SUMMARY: SummaryItem[] = [
  { field: "product_idea", label: "상품 아이디어", value: "한글을 활용한 파우치", source: "user_free_text", source_label: "직접 입력", confidence: 1, is_assumption: false },
  { field: "user", label: "사용자", value: "일상 소지품을 정리하는 사람", source: "user_selected_ai_option", source_label: "선택지에서 고름", confidence: 1, is_assumption: false },
];

const DONE_SUMMARY: SummaryItem[] = [
  ...SUMMARY,
  { field: "usage_context", label: "사용 상황", value: "가방 안의 작은 물건을 찾기 쉽게", source: "user_selected_ai_option", source_label: "선택지에서 고름", confidence: 1, is_assumption: false },
  { field: "core_value", label: "핵심 가치", value: "한글 형태를 일상 소품으로 즐긴다", source: "user_free_text", source_label: "직접 입력", confidence: 1, is_assumption: false },
  { field: "price_direction", label: "가격 방향", value: "1~3만원", source: "ai_assumption", source_label: "AI 가정", confidence: 0.5, is_assumption: true },
];

const SUPPLEMENT_EMPTY: SupplementItem[] = [
  { name: "target_customer", label: "고객", example: "일상 소지품을 정리하는 사용자", value: null },
  { name: "material", label: "소재", example: "면 100%", value: null },
  { name: "size", label: "크기", example: "가로 20 × 세로 12cm", value: null },
  { name: "production_cost", label: "제작 비용", example: "8,000원 / 개", value: null },
  { name: "sale_price", label: "판매 가격", example: "18,000원 / 개", value: null },
];

const SUPPLEMENT_FILLED: SupplementItem[] = SUPPLEMENT_EMPTY.map((item) =>
  item.name === "material" || item.name === "sale_price" ? { ...item, value: item.example } : item,
);

const SESSION_BASE: SessionView = {
  session_id: "sess_preview",
  task_type: "product_planning",
  mode: "standard",
  status: "clarifying",
  raw_input: REQUEST,
  next_question: QUESTION,
  progress: { asked: 1, cap: 5, readiness: 0.38 },
  summary: SUMMARY,
  unknowns: [],
  supplements: SUPPLEMENT_EMPTY,
  supplements_changed: false,
  flow: [ANSWERED_USER, current(QUESTION), ...UPCOMING],
  can_generate: true,
  has_result: false,
  result_stale: false,
  error: null,
};

export const SESSION_QUESTION: SessionView = SESSION_BASE;
export const SESSION_LADDER: SessionView = {
  ...SESSION_BASE,
  next_question: LADDER_QUESTION,
  progress: { ...SESSION_BASE.progress, asked: 2 },
  flow: [ANSWERED_USER, current(LADDER_QUESTION), ...UPCOMING.slice(0, 2)],
};
export const SESSION_PROPOSAL: SessionView = {
  ...SESSION_LADDER,
  next_question: PROPOSAL_QUESTION,
  flow: [ANSWERED_USER, current(PROPOSAL_QUESTION), ...UPCOMING.slice(0, 2)],
};

const READY: SessionView = {
  ...SESSION_BASE,
  status: "confirming",
  next_question: null,
  progress: { asked: 4, cap: 5, readiness: 0.82 },
  summary: DONE_SUMMARY,
  unknowns: [{ field: "customer_problem", label: "고객 문제" }],
  flow: DONE_FLOW,
};

export const SESSION_READY: SessionView = READY;
export const SESSION_FAILED: SessionView = {
  ...READY,
  status: "failed",
  error: "결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요.",
};
export const SESSION_DONE: SessionView = { ...READY, status: "completed", has_result: true };
export const SESSION_STALE: SessionView = { ...READY, status: "revising", has_result: true, result_stale: true };

export const RESULT: ResultView = {
  session_id: "sess_preview",
  status: "completed",
  stale: false,
  version: { version: 2, created_at: "2026-10-16T09:30:00Z", reason: "regenerate", saved: false },
  summary: DONE_SUMMARY,
  unknowns: [{ field: "customer_problem", label: "고객 문제" }],
  supplements: SUPPLEMENT_EMPTY,
  validation: {
    issues: [{ rule: "unverified_number", message: "가격은 AI 가정이에요. 비슷한 상품 가격을 확인해 주세요.", severity: "warning" }],
    passed: true,
  },
  result: {
    sections: [
      { order: 1, heading: "상품 콘셉트", kind: "diagnosis", blocks: [{ type: "text", text: "가방 안의 작은 물건을 정리하는 한글 파우치.\n한글 형태를 일상 소품으로 즐기게 한다." }] },
      { order: 2, heading: "핵심 기능", kind: "suggestion", blocks: [{ type: "text", text: "작은 소지품이 섞이지 않게 칸을 나누고, 한글 자모를 겉면 패턴으로 쓴다." }] },
      { order: 3, heading: "첫 제작 방향", kind: "suggestion", blocks: [{ type: "text", text: "수납과 사용 편의를 우선한다. 소재와 봉제 가능성을 먼저 확인한다." }] },
      { order: 4, heading: "다음 실행", kind: "action", blocks: [{ type: "text", text: "잠재 고객 다섯 명에게 시제품 사진을 보여 주고 구매 이유와 우려를 듣는다." }] },
    ],
    evidence: [],
    assumptions: [
      { field: "price_direction", label: "가격 방향", value: "1~3만원", reason: "비슷한 소형 파우치의 가격대", requires_confirmation: true },
    ],
    full_text: "상품 콘셉트\n가방 안의 작은 물건을 정리하는 한글 파우치.",
    content: {},
    generated_at: "2026-10-16T09:00:00Z",
  },
};

/** 미확인 정보 두 개를 입력했고 아직 초안에 반영하지 않았다. */
export const SESSION_SUPPLEMENT: SessionView = {
  ...READY,
  status: "revising",
  has_result: true,
  result_stale: true,
  supplements: SUPPLEMENT_FILLED,
  supplements_changed: true,
};

/** 보완 정보를 반영한 새 버전(V3). */
export const SESSION_SUPPLEMENTED: SessionView = { ...SESSION_SUPPLEMENT, status: "completed", result_stale: false, supplements_changed: false };
export const RESULT_SUPPLEMENTED: ResultView = {
  ...RESULT,
  version: { version: 3, created_at: "2026-10-16T10:00:00Z", reason: "supplement", saved: false },
  supplements: SUPPLEMENT_FILLED,
};

export const SAVED_VERSION: VersionView = {
  session_id: "sess_preview",
  version: { ...RESULT.version, saved: true },
  latest: true,
  result: RESULT.result,
  validation: RESULT.validation,
  summary: RESULT.summary,
  unknowns: RESULT.unknowns,
  supplements: RESULT.supplements,
};

export const OLD_VERSION: VersionView = {
  session_id: "sess_preview",
  version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true },
  latest: false,
  result: { ...RESULT.result, sections: RESULT.result.sections.slice(0, 2) },
  validation: null,
  summary: SUMMARY,
  unknowns: [{ field: "usage_context", label: "사용 상황" }],
  supplements: SUPPLEMENT_EMPTY,
};

export const SESSIONS: SessionSummary[] = [
  {
    session_id: "sess_preview",
    task_type: "product_planning",
    title: "상품기획",
    raw_input: REQUEST,
    mode: "standard",
    has_question: false,
    has_result: true,
    result_stale: false,
    latest_version: 2,
    saved_versions: [
      { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true },
      { version: 2, created_at: "2026-10-16T09:30:00Z", reason: "regenerate", saved: true },
    ],
    updated_at: "2026-10-16T09:30:00Z",
  },
  {
    session_id: "sess_brand",
    task_type: "branding",
    title: "브랜딩",
    raw_input: "한글 파우치 브랜드가 너무 전통적으로만 보이지 않으면 좋겠어요",
    mode: "quick",
    has_question: true,
    has_result: false,
    result_stale: false,
    latest_version: null,
    saved_versions: [],
    updated_at: "2026-10-16T08:10:00Z",
  },
];

// 결과 이미지 자리표시(백엔드 Mock과 같은 모양). 갤러리는 백엔드 없이 그리므로 data URL로 둔다
const PREVIEW_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><rect width="640" height="360" fill="#f4f1ee"/><circle cx="250" cy="170" r="56" fill="#e3d6cf"/><rect x="330" y="120" width="120" height="100" rx="12" fill="#d6c3b8"/><rect x="190" y="250" width="260" height="14" rx="7" fill="#e3d6cf"/></svg>';
export const PREVIEW_IMAGE_ID = "asset_preview";
export const PREVIEW_IMAGES = { [PREVIEW_IMAGE_ID]: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(PREVIEW_SVG)}` };

/** backend/app/harness/tasks/product_planning/evidence.yaml과 같은 두 자료. */
export const EVIDENCE_ITEMS: EvidenceItem[] = [
  {
    id: "ykk_zipper_caution",
    title: "제작 점검 · 지퍼 사용상 주의",
    publisher: "YKK KOREA",
    meta: "제조사 기술 안내 · 작성일 미표기 · 확인 2026.10.15",
    summary: "가방을 가득 채운 상태에서 지퍼를 억지로 닫으면 손상될 수 있으며, 봉제 시 옷감 끼임에 주의하도록 안내합니다.",
    scope: "적용: 지퍼 여밈을 선택할 때의 점검 참고. 이 상품의 품질시험 결과는 아닙니다.",
    url: "https://ykkkorea.com/support/caution/caution",
    applies_to: "suggestion",
    record: {
      title: "제작 점검 항목",
      text: "지퍼 여밈을 선택할 경우, 내용물을 넣고 여닫기와 안감 끼임을 점검합니다.",
      note: "제품 시험 전",
      caution: "제작 점검 항목을 추가하는 단계이며, 제품 성능이 검증된 것은 아니에요.",
    },
  },
  {
    id: "kcdf_craft_trend_fair_2025",
    title: "시장 배경 · 2025 공예트렌드페어 결과",
    publisher: "한국공예·디자인문화진흥원",
    meta: "보도자료 · 작성 2026.01.12 · 확인 2026.10.15",
    summary: "공예 사업체 311개가 참여한 행사에서 전시·판매·구매자 상담이 진행된 사례를 소개합니다.",
    scope: "적용: 공예 유통 경로를 살펴보는 배경 자료. 이 상품의 수요·매출 근거로 사용하지 않습니다.",
    url: "https://www.kcdf.or.kr/brd/board/324/L/menu/293?bbIdx=8680&brdType=R",
    applies_to: "diagnosis",
    record: null,
  },
];

/** 근거를 반영한 결과(V3): 첫 제안 섹션(핵심 기능, order 2) 뒤에 점검 기록. */
export const RESULT_EVIDENCE: ResultView = {
  ...RESULT,
  version: { version: 3, created_at: "2026-10-16T10:10:00Z", reason: "evidence", saved: false },
  result: {
    ...RESULT.result,
    evidence: [
      {
        source_id: "ykk_zipper_caution",
        title: "제작 점검 항목",
        text: "지퍼 여밈을 선택할 경우, 내용물을 넣고 여닫기와 안감 끼임을 점검합니다.",
        note: "제품 시험 전",
        source_title: "제작 점검 · 지퍼 사용상 주의",
        publisher: "YKK KOREA",
        url: "https://ykkkorea.com/support/caution/caution",
        section_kind: "suggestion",
        section_order: 2,
      },
    ],
  },
};

/** 이미지 블록이 있는 결과(브랜딩처럼 이미지를 켠 과제의 모습). 둘째 섹션 끝에 이미지 한 장. */
export const RESULT_IMAGE: ResultView = {
  ...RESULT,
  result: {
    ...RESULT.result,
    sections: RESULT.result.sections.map((s) =>
      s.order === 2
        ? {
            ...s,
            blocks: [
              ...s.blocks,
              { type: "image", asset_id: PREVIEW_IMAGE_ID, alt: "핵심 기능 참고 이미지", caption: "AI가 만든 참고 이미지예요. 실제 결과물과 다를 수 있어요.", origin: "ai_generated" },
            ],
          }
        : s,
    ),
  },
};
