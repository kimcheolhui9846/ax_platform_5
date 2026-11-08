// 미리보기 갤러리의 샘플 값. 생성된 API 타입을 쓰므로 계약이 바뀌면 빌드가 깨져 바로 알 수 있다.
import type { CloseView, EvidenceItem, InventoryView, InventoryItem as Item, ItemView, ReorderPolicy, FlowItem, Question, ResultView, SessionContext, SessionSummary, SessionView, SummaryItem, SupplementItem, TaskForm, TaskSummary, VersionView } from "../api/types";
import type { EditableFlowItem } from "../lib/flowView";
import { initialInventoryState } from "../inventory/state";
import type { InventoryState } from "../inventory/state";

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
  {
    task_type: "ir_pitch",
    title: "IR 피치덱",
    description: "투자자를 설득할 발표 흐름과 슬라이드별 원고를 정리해요.",
    heading: "투자자 앞에서 발표할 자료가 필요해요",
    deliverable: "피치덱 슬라이드 · 발표 원고",
    evidence_sources: 0,
  },
];

export const PRODUCT = TASKS[1];

export const REQUEST = "한글을 활용한 파우치를 만들고 싶은데, 어떤 상품으로 만들면 좋을까요?";

export const FORM: TaskForm = {
  task_type: "product_planning",
  title: "상품기획",
  description: PRODUCT.description,
  input_placeholder: "예) 외국인 관광객 선물용 한글 북백",
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
  { field: "product_idea", label: "상품 아이디어", value: "한글을 활용한 파우치", source: "user_free_text", source_label: "직접 입력", confidence: 1, is_assumption: false, private: false },
  { field: "user", label: "사용자", value: "일상 소지품을 정리하는 사람", source: "user_selected_ai_option", source_label: "선택지에서 고름", confidence: 1, is_assumption: false, private: false },
];

const DONE_SUMMARY: SummaryItem[] = [
  ...SUMMARY,
  { field: "usage_context", label: "사용 상황", value: "가방 안의 작은 물건을 찾기 쉽게", source: "user_selected_ai_option", source_label: "선택지에서 고름", confidence: 1, is_assumption: false, private: false },
  { field: "core_value", label: "핵심 가치", value: "한글 형태를 일상 소품으로 즐긴다", source: "user_free_text", source_label: "직접 입력", confidence: 1, is_assumption: false, private: false },
  { field: "price_direction", label: "가격 방향", value: "1~3만원", source: "ai_assumption", source_label: "AI 가정", confidence: 0.5, is_assumption: true, private: false },
];

const SUPPLEMENT_EMPTY: SupplementItem[] = [
  { name: "target_customer", label: "고객", example: "일상 소지품을 정리하는 사용자", value: null, private: false },
  { name: "material", label: "소재", example: "면 100%", value: null, private: false },
  { name: "size", label: "크기", example: "가로 20 × 세로 12cm", value: null, private: false },
  { name: "production_cost", label: "제작 비용", example: "8,000원 / 개", value: null, private: false },
  { name: "sale_price", label: "판매 가격", example: "18,000원 / 개", value: null, private: false },
];

const SUPPLEMENT_FILLED: SupplementItem[] = SUPPLEMENT_EMPTY.map((item) =>
  item.name === "material" || item.name === "sale_price" ? { ...item, value: item.example } : item,
);

const SESSION_BASE: SessionView = {
  session_id: "sess_preview",
  task_type: "product_planning",
  name: "수제 향초",
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
  context: null,
  error: null,
  private_names: [],
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
/** 질문 항목(사용 상황)이 AI에 보내지 않음으로 정해진 상태: 체크 칸이 처음부터 체크돼 있다. */
export const SESSION_QUESTION_PRIVATE: SessionView = { ...SESSION_BASE, private_names: ["usage_context"] };
/** 기준 표에 AI에 보내지 않은 값(핵심 가치)이 표시된 확인 화면. */
export const SESSION_READY_PRIVATE: SessionView = {
  ...READY,
  summary: DONE_SUMMARY.map((item) => (item.field === "core_value" ? { ...item, private: true } : item)),
  private_names: ["core_value"],
};
/** 판매 가격을 AI에 보내지 않기로 한 보완 항목. */
export const SUPPLEMENT_PRIVATE: SupplementItem[] = SUPPLEMENT_FILLED.map((item) => (item.name === "sale_price" ? { ...item, private: true } : item));
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

/** 사업계획 V2에서 상품기획으로 이어 온 기준(백엔드 build_context가 만드는 모양: 대상 과제의 필드·라벨). */
export const CONTEXT: SessionContext = {
  session_id: "sess_preview_plan",
  task_type: "business_plan",
  version: 2,
  title: "사업계획 초안 V2",
  summary: "한글 디자인 소품을 온라인으로 파는 1인 사업. 첫 상품은 작은 소지품을 정리하는 파우치로 시작한다.",
  items: [
    { field: "product_idea", label: "상품 아이디어", value: "한글을 활용한 파우치", private: false },
    { field: "user", label: "사용자", value: "작은 소지품을 들고 다니는 직장인", private: false },
  ],
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
    name: "수제 향초 상품기획",
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
    name: "한글 파우치 브랜드",
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

/** 이미지 블록이 있는 결과(브랜딩처럼 이미지를 켠 과제의 모습). 첫 섹션 끝에 이미지 한 장. */
export const RESULT_IMAGE: ResultView = {
  ...RESULT,
  result: {
    ...RESULT.result,
    sections: RESULT.result.sections.map((s) =>
      s.order === 1
        ? {
            ...s,
            blocks: [
              ...s.blocks,
              { type: "image", asset_id: PREVIEW_IMAGE_ID, alt: "상품 콘셉트 참고 이미지", caption: "AI가 만든 참고 이미지예요. 실제 결과물과 다를 수 있어요.", origin: "ai_generated" },
            ],
          }
        : s,
    ),
  },
};

// ---- 재고 ----

const KG = "kg";
const item = (item_id: string, name: string, patch: Partial<Item> = {}): Item => ({
  item_id,
  name,
  option: null,
  kind: "material",
  unit: KG,
  procurement: "purchase",
  supplier_id: "sup-1",
  archived: false,
  ...patch,
});
const POLICY: ReorderPolicy = { min_stock: "10", target_stock: "40", purchase_unit: "10", lead_days: 3, unit_price: "4500" };
const itemView = (i: Item, patch: Partial<ItemView> = {}): ItemView => ({
  item: i,
  on_hand: "25",
  in_transit: "0",
  status: "ok",
  suggested_quantity: null,
  policy: POLICY,
  last_counted_at: "2026-11-07T18:00:00Z",
  suggestion: null,
  auto_order: null,
  ...patch,
});

/** 재고 샘플: 부족·미입력·배송 중·충분·제작품·숨김 품목 하나씩. */
export const INVENTORY: InventoryView = {
  items: [
    itemView(item("it-1", "국산 밀가루", { option: "강력분 20kg" }), { on_hand: "4", status: "short", suggested_quantity: "40" }),
    itemView(item("it-2", "설탕"), { on_hand: null, status: "uncounted", last_counted_at: null }),
    itemView(item("it-3", "포장 박스", { kind: "packaging", unit: "개" }), { on_hand: "30", in_transit: "100", status: "in_transit" }),
    itemView(item("it-4", "유기농 버터", { option: "무염" }), { on_hand: "26" }),
    itemView(item("it-5", "수제 쿠키 세트", { kind: "finished", unit: "세트", procurement: "make", supplier_id: null }), { on_hand: "12", policy: null }),
    itemView(item("it-6", "단종 리본", { kind: "packaging", unit: "롤", archived: true }), { on_hand: "0" }),
  ],
  suppliers: [
    { supplier_id: "sup-1", name: "한빛 식자재", kind: "mock", mock_outcome: "accept" },
    { supplier_id: "sup-2", name: "새벽 포장", kind: "mock", mock_outcome: "price_changed" },
  ],
  settings: { address: "서울시 마포구 월드컵로 1", anomaly_drop_ratio: "0.5", stale_days: 7 },
  last_close: { close_id: "cl-1", close_date: "2026-11-07", counts: { "it-1": "4", "it-4": "26" }, at: "2026-11-07T18:00:00Z" },
  orders: [],
  holds: [],
};

export const INVENTORY_EMPTY: InventoryView = { ...INVENTORY, items: [], suppliers: [], last_close: null };

/** 하루 마감 입력 샘플(센 수량 일부, 이상 수량 2개 중 하나만 확인). */
export const CLOSE_INPUT: InventoryState["close"] = {
  ...initialInventoryState("2026-11-08").close,
  counts: { "it-1": "3", "it-2": "18", "it-4": "90" },
};
export const CLOSE_CHECKED: InventoryState["close"] = {
  ...CLOSE_INPUT,
  check: {
    anomalies: [
      { item_id: "it-1", previous: "4", counted: "3", kind: "drop" },
      { item_id: "it-4", previous: "26", counted: "90", kind: "increase" },
    ],
  },
  confirmed: ["it-4"],
};
export const CLOSE_RESULT: CloseView = {
  close: { close_id: "cl-2", close_date: "2026-11-08", counts: CLOSE_INPUT.counts, at: "2026-11-08T18:00:00Z" },
  inventory: INVENTORY,
  auto_orders: [
    { item_id: "it-1", order_id: "ord-1", status: "accepted", hold_reason: null },
    { item_id: "it-2", order_id: null, status: null, hold_reason: "price_changed" },
  ],
};
export const CLOSE_DONE: InventoryState["close"] = { ...initialInventoryState("2026-11-08").close, result: CLOSE_RESULT };
