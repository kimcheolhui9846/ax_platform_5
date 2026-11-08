# 재고 화면 2(주문·입고·보류·자동 주문) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 재고 현황에서 부족한 구매 품목을 거래처별로 주문하고(S06 제안 → S07 주문 확인), '주문·입고' 탭에서 주문 상태·남은 수량을 보고 입고하며(S11), 보류를 재조회·직접 검토·해결하고(S10), '자동 주문' 탭에서 품목별 자동 주문을 켜고 끄고 한도를 정한다(S09·S08). 인수 테스트(TC9)와 테스트 케이스 문서를 더한다.

**Architecture:** 재고 화면 1(PR #44)의 구조를 그대로 따른다: `api/inventory.ts`(호출, 주문·입고·보류·자동 주문 함수는 이미 있다) → `inventory/state.ts`(순수 reducer) → `inventory/screenModel.ts`(순수) → `screens/inventory/*`(props만) → `inventory/view.tsx`(`InventoryView`)·`inventory/handlers.ts`·`InventoryApp`. 탭 두 개(`orders`·`auto`)를 더한다. 주문 확인(S07)은 탭과 상관없이 탭 줄 아래에 뜨는 카드다(주문 초안은 reducer가 가진다: 멱등 `request_id`를 다시 시도까지 지키려고).

**Tech Stack:** React 19, TypeScript, Vite, vitest(`react-dom/server`의 `renderToString` — @testing-library는 설치돼 있지 않다), openapi-fetch. 백엔드 인수 테스트는 pytest(`backend/tests/acceptance/`).

**설계:** `docs/superpowers/specs/2026-11-08-inventory-design.md` 3장(거래처와 주문)·5장(API)·6장(화면)·7장(테스트). IA 원본 `design/2026-11-05-ia-inventory-proposal/AX_IA.md`의 S06~S11.

## Global Constraints

- 모든 명령은 저장소 루트에서: `npm --prefix frontend test`, `npm --prefix frontend run build`, `uv run --directory backend pytest -q`. 백엔드 앱 코드는 바꾸지 않는다(인수 테스트와 TC 문서만 더한다).
- TDD: 순수 함수(routes·reducer·screenModel·handlers·format)는 먼저 실패하는 테스트. 화면 부품은 `renderToString`으로 렌더 테스트.
- 코드 품질(`CLAUDE.md`): 판단은 순수 함수, 상태 변경은 reducer 한 곳, 컴포넌트는 props만(부품 안에서 끝나는 UI 상태만 부품이 가진다), 제어 플래그 인자 금지, 필요한 값만 넘긴다.
- 백엔드 호출은 `frontend/src/api/inventory.ts`만. `schema.d.ts`는 손대지 않는다. 주소는 `lib/routes.ts`의 `parseRoute`·`toHash`에서만.
- 색·글자 크기·폭·선·모서리는 `styles/tokens.css`의 `var(--…)`만(`tokens.test.ts`). 새 CSS는 `styles/inventory.css`.
- 수량·금액은 API 문자열이다. 보유·배송 중·남은 수량 판단은 서버 값으로 한다. **예외 하나**: 주문 확인 카드의 '예상 총액'은 화면이 줄마다 수량 × 단가를 0.01로 반올림해 더한 값이다(서버 `rules.line_amount`와 같은 규칙, 표시용. 실제 총액은 주문 응답의 `total`).
- 미입력(`on_hand: null`)은 0이 아니다.
- 사용자에게 보이는 문구는 한국어. 오류는 서버 `detail`을 알림(`Toast`)으로.
- 요청 중엔 그 버튼을 막고 진행 글('주문 중…'·'확인 중…'·'저장 중…'), 실패하면 입력을 둔 채 알림.
- 커밋 메시지는 한국어, AI 공동저자·생성 표기 금지. 브랜치 `task/45-inventory-screens-2`(PR #44 브랜치 위). 푸시는 마지막에.

## 결정 사항

| 질문 | 결정 | 이유 |
|---|---|---|
| S06 제안은 어디에 | 재고 현황 탭, 요약 아래 '부족한 구매 품목' 묶음(거래처별 카드: 품목·제안량·단가, '주문 확인' 버튼) | 서버가 한 주문에 한 거래처만 받는다(`INVENTORY_MIXED_SUPPLIER_MESSAGE`) |
| S07 주문 확인은 대화상자인가 | 탭 줄 아래 카드(모든 탭에서 보인다). 줄마다 수량 입력(제안량으로 시작), 단가, 예상 총액, 배송지, '주문하기'·'취소' | 모달은 미리보기·html.to.design에서 다루기 어렵고 와이어프레임 전이다. 보류의 '새 단가로 다시 주문'도 같은 카드를 연다 |
| `request_id`는 누가 만드나 | 주문 초안을 열 때 handlers가 주입받은 `newRequestId()`로 만들어 reducer 초안에 둔다(`manual:{uuid}`). 실패 뒤 다시 누르면 같은 id(네트워크 실패로 서버에 들어갔어도 두 번 주문하지 않는다). 성공하면 초안이 사라진다 | 설계 3장 멱등 |
| 주문 결과 안내 | 주문 응답의 상태로 문구: 접수 '주문이 접수됐어요', 거절 '주문이 거절됐어요: {보류 사유}', 불명 '접수 여부를 확인하지 못했어요. 주문·입고 탭에서 다시 확인해 주세요'. 카드 자리에 안내와 '주문·입고 보기' 버튼 | |
| 입고 양식 상태 | 주문 카드 안 부품 상태(줄마다 수량 = 남은 수량으로 시작, '이미 마감에서 셌어요' 체크). key = 입고 성공 횟수 + 주문 `updated_at` | 부품 안에서 끝나는 UI 상태 |
| 자동 주문 편집(S08) 상태 | 품목을 고르면 편집 카드(부품 상태: 켜기·동의 체크·1회 한도·월 한도). key = 저장 성공 횟수 + 품목 + 설정 값 | 화면 1의 양식과 같은 방식 |
| 저장하지 않은 입력 | 입고·자동 주문 양식도 `edited`(양식 `receipt`·`auto`)로 센다. 주문 초안은 탭을 옮겨도 남으므로 세지 않는다 | |

## File Structure

| 파일 | 할 일 |
|---|---|
| Modify `frontend/src/lib/routes.ts`(+test) | `InventoryTab`에 `"orders" \| "auto"`, `#/inventory/orders`·`#/inventory/auto`. 탭 순서 `stock, close, orders, auto, items` |
| Modify `frontend/src/inventory/view.tsx` | 탭 이름표 `orders: "주문·입고"`, `auto: "자동 주문"`, `InventoryScreenModel`에 `orders`·`auto`, 주문 확인 카드 자리 |
| Modify `frontend/src/inventory/state.ts`(+test) | 호출 종류·양식, 주문 초안·결과 |
| Modify `frontend/src/lib/inventory/format.ts`(+test) | 주문 출처·예상 총액 |
| Modify `frontend/src/inventory/screenModel.ts`(+test) 또는 새 `inventory/orderModel.ts`(+test) | 제안·주문 확인·주문 목록·보류·자동 주문 화면 모델 |
| Modify `frontend/src/inventory/screen.ts`(+test) | 탭 → 화면 모델 |
| Modify `frontend/src/inventory/handlers.ts`(+test) | 주문·재조회·입고·보류 해결·자동 주문 |
| Create `frontend/src/screens/inventory/OrderProposal.tsx`, `OrderConfirm.tsx`, `OrdersScreen.tsx`, `AutoOrderScreen.tsx` | S06·S07·S10/S11·S09/S08 |
| Modify `frontend/src/screens/inventory/StockScreen.tsx` | 제안 묶음 |
| Modify `frontend/src/inventory/InventoryApp.tsx` | `newRequestId` 주입 |
| Modify `frontend/src/preview/fixtures.ts`·`frames.tsx`·`handlers.ts` | 새 프레임 |
| Modify `frontend/src/styles/inventory.css` | 새 화면 배치(토큰만) |
| Create `backend/tests/acceptance/test_tc9_inventory.py`, Modify `docs/test-cases.yaml`, `docs/TEST-CASES.xlsx` | TC9 |
| Docs | `CLAUDE.md`, `docs/HANDOFF.md`, `docs/WBS.xlsx` 4.15 |

---

### Task 1: 탭 두 개와 상태(주문 초안)

**Files:** `lib/routes.ts`·test, `inventory/view.tsx`(탭 이름표·`inventoryTitle`만), `inventory/state.ts`·test.

**Interfaces (Produces):**
- `InventoryTab = "stock" | "close" | "orders" | "auto" | "items"`, `INVENTORY_TABS = ["stock","close","orders","auto","items"]`. `parseRoute("#/inventory/orders")` → orders, `"#/inventory/auto"` → auto. 왕복 테스트.
- `INVENTORY_TAB_LABELS`에 `orders: "주문·입고"`, `auto: "자동 주문"`. `inventoryTitle("orders")` → `"창작자 AX · 재고 주문·입고"`.
- `InventoryCall = "load" | "save" | "check" | "close" | "suggest" | "order" | "refresh" | "resolve"`.
- `InventoryForm`에 `"receipt" | "auto"`를 더한다(`saved` 초기값도). 입고 요청은 `kind: "save", form: "receipt"`, 자동 주문 저장은 `kind: "save", form: "auto"`.
- 주문 초안:
  ```ts
  export type OrderDraftLine = { itemId: string; quantity: string; unitPrice: string }; // unitPrice: 기준 단가 또는 보류의 새 단가
  export type OrderDraft = { requestId: string; supplierId: string; lines: OrderDraftLine[]; repriced: boolean }; // repriced: 보류의 새 단가로 연 초안(요청에 unit_price를 싣는다)
  // InventoryState에 더한다
  order: OrderDraft | null;
  orderResult: OrderResultNotice | null; // 마지막 주문 응답 안내
  export type OrderResultNotice = { status: OrderStatus; holdReason: HoldReason | null };
  ```
- 새 action:
  - `{ type: "orderOpened"; draft: OrderDraft }` → `order = draft`, `orderResult = null`.
  - `{ type: "orderQuantityChanged"; itemId: string; quantity: string }` → 그 줄 수량만 바꾼다.
  - `{ type: "orderLineRemoved"; itemId: string }` → 줄을 뺀다(마지막 줄이면 초안을 닫는다).
  - `{ type: "orderCancelled" }` → `order = null`. 기다리는 `order` 요청이 있으면 그 응답은 그래도 받는다(서버가 이미 주문했을 수 있다 — 화면 1 최종 리뷰의 마감 저장과 같은 이유).
  - `{ type: "ordered"; seq: number; order: Order; view: InventoryView }` → `isCurrent`일 때만: `view` 갱신, `order = null`, `orderResult = { status: order.status, holdReason: 그 주문의 미해결 보류 사유(view.holds에서 order_id가 같은 첫 보류) ?? null }`, `inflight = null`.
  - `{ type: "orderResultClosed" }` → `orderResult = null`.
- `discarded`·`closeReset`은 주문 초안을 건드리지 않는다.

- [ ] routes 테스트 → 구현, state 테스트(각 action, 늦은 `ordered` 버림, 취소 뒤에도 기다리던 `ordered`는 받음, `receipt`·`auto` 저장 횟수) → 구현.
- [ ] `npm --prefix frontend test`·`build` → 커밋 "재고 화면 2: 주문·자동 주문 탭과 주문 초안 상태".

### Task 2: 화면 모델(제안·주문 확인·주문·보류·자동 주문)

**Files:** 새 `inventory/orderModel.ts`·test(재고 `screenModel.ts`가 커지지 않게), `lib/inventory/format.ts`·test, `inventory/screen.ts`·test, `inventory/view.tsx`(`InventoryScreenModel` 확장만).

**Interfaces (Produces):**
- `format.ts`:
  - `ORIGIN_LABELS: Record<OrderOrigin, string> = { manual: "직접 주문", auto: "자동 주문" }`(타입 `OrderOrigin`이 `api/types.ts`에 없으면 `Order["origin"]`으로 별칭을 더한다).
  - `lineAmount(quantity: string, unitPrice: string): string | null` — 둘 다 숫자 글이면 수량 × 단가를 0.01 반올림(반올림은 절반 올림)한 금액 글("12500.00" 형태, 소수 둘째 자리), 아니면 null. 정수 센트 계산으로 부동소수 오차를 피한다(수량 소수 자리는 최대 3자리로 본다).
  - `sumAmounts(amounts: string[]): string`(센트 합).
- `orderModel.ts`:
  ```ts
  export type ProposalGroup = { supplierId: string; supplierName: string; lines: { itemId: string; name: string; unit: string; suggested: string; unitPrice: string }[] };
  export function orderProposals(view: InventoryView): ProposalGroup[];
  ```
  숨기지 않은 구매 품목 중 `status === "short"`이고 `suggested_quantity`·`policy`·`supplier_id`가 있는 것, 거래처별(거래처 이름순, 그 안에서 품목 이름순). `suggested`는 서버 값 그대로(문자열, 소수 끝 0 제거 없이 숫자 글 — 수량 입력 시작값으로 쓰므로), `unitPrice`는 `policy.unit_price`.
  ```ts
  export function draftFromProposal(group: ProposalGroup, requestId: string): OrderDraft; // repriced false
  export function draftFromHold(view: InventoryView, holdId: string, requestId: string): OrderDraft | null;
  ```
  `draftFromHold`: 보류가 `price_changed`이고 `current_unit_price`가 있고 품목이 주문 가능(구매·거래처·기준)할 때만. 수량은 그 보류 주문의 같은 품목 줄 수량(주문이 없으면 품목의 `suggested_quantity`, 그것도 없으면 null 반환), 단가는 `current_unit_price`, `repriced: true`.
  ```ts
  export type OrderConfirmModel = {
    supplierName: string; address: string; addressMissing: boolean;
    lines: { itemId: string; name: string; unit: string; quantity: string; unitPriceText: string; amountText: string; valid: boolean }[];
    totalText: string; canSubmit: boolean; repriced: boolean;
  };
  export function orderConfirmModel(view: InventoryView, draft: OrderDraft): OrderConfirmModel;
  ```
  `valid` = 수량이 양수 숫자 글(`/^\d+(\.\d+)?$/`이고 0보다 큼). `canSubmit` = 줄이 있고 모두 valid이고 배송지가 있다. `amountText`는 `moneyText(lineAmount(...))` 또는 `"-"`, `totalText`는 valid 줄 합의 `moneyText`.
  ```ts
  export function orderResultText(notice: OrderResultNotice): string; // 결정 사항 표의 문구, 거절은 HOLD_LABELS[holdReason] (없으면 '주문이 거절됐어요')
  export type OrderCard = {
    orderId: string; supplierName: string; originLabel: string; statusLabel: string; status: OrderStatus; createdDate: string; totalText: string;
    lines: { itemId: string; name: string; unit: string; ordered: string; received: string; remaining: string; remainingRaw: string }[];
    canRefresh: boolean; canReceive: boolean;
  };
  export function orderCards(view: InventoryView): OrderCard[]; // 서버 순서(최근 것 먼저). canRefresh = unknown, canReceive = accepted|partially_received. remaining = 주문 수량 − 입고(서버 값의 차, 표시는 quantityText; remainingRaw는 입고 양식 시작값)
  export type HoldRow = { holdId: string; itemName: string; reasonLabel: string; createdDate: string; orderId: string | null; canReview: boolean; canRefresh: boolean; priceText: string | null };
  export function holdRows(view: InventoryView): HoldRow[]; // 미해결만. canReview = draftFromHold가 null이 아님, canRefresh = 보류 주문이 unknown, priceText = 새 단가 moneyText
  export type AutoRow = { itemId: string; name: string; orderable: boolean; reason: string; enabled: boolean; limitsText: string; lastResult: string };
  export function autoRows(view: InventoryView): AutoRow[]; // 숨기지 않은 구매 품목. orderable = 거래처·기준 있음, 아니면 reason '거래처와 보충 기준이 필요해요'. lastResult = 그 품목의 가장 최근 자동 주문 상태 라벨 + 날짜, 미해결 자동 보류가 더 최근이면 그 사유, 없으면 '아직 없음'
  export type AutoModel = { rows: AutoRow[]; addressMissing: boolean };
  export function autoModel(view: InventoryView): AutoModel;
  ```
  '남은 수량'을 화면에서 빼는 것은 두 서버 값의 차라 계산 금지 원칙의 예외로 둔다(센트처럼 정수 단위로 계산, `lineAmount`와 같은 소수 처리).
- `InventoryScreenModel`에 `{ kind: "orders"; orders: OrderCard[]; holds: HoldRow[] }`, `{ kind: "auto"; model: AutoModel; items: ItemView[] }`(편집 카드가 품목의 현재 설정을 읽는다), stock 모델에 `proposals: ProposalGroup[]`.
- `inventoryScreen(state, tab)`이 새 탭을 만든다.

- [ ] format·orderModel·screen 테스트(경계: 거래처 없는 품목 제외, 숨긴 품목 제외, 제작 품목 제외, 보류 단가, 반올림 0.005 → 0.01, 남은 수량 0, 해결된 보류 제외) → 구현 → 커밋 "재고 화면 2: 주문·보류·자동 주문 화면 모델".

### Task 3: 핸들러

**Files:** `inventory/handlers.ts`·test, `inventory/view.tsx`(`InventoryHandlers` 타입), `inventory/InventoryApp.tsx`(`newRequestId` 주입: `() => "manual:" + crypto.randomUUID()`), `preview/handlers.ts`(noop).

**Interfaces (Produces):** `Deps`에 `newRequestId: () => string`. `InventoryHandlers`에:
- `onOpenOrder(supplierId: string)` → 제안 묶음에서 `draftFromProposal`로 `orderOpened`(묶음이 없으면 아무것도 안 함).
- `onOrderQuantity(itemId, quantity)`, `onOrderRemoveLine(itemId)`, `onOrderCancel()`, `onOrderResultClose()`.
- `onPlaceOrder()` → `run({ kind: "order", request: () => placeOrder({ request_id, lines }), done: (r, seq) => ({ type: "ordered", seq, order: r.order, view: r.inventory }) })`. `lines`: 줄마다 `{ item_id, quantity: trim, unit_price }`이고 `unit_price`는 `repriced`일 때만 싣는다. 초안이 없거나 `canSubmit`이 아니면 아무것도 안 함.
- `onRefreshOrder(orderId)` → `kind: "refresh"`, 응답 `OrderView`의 `inventory`로 `loaded`.
- `onReceive(orderId, lines: { item_id: string; quantity: string; already_counted: boolean }[])` → `kind: "save", form: "receipt"`, 응답 `inventory`로 `loaded`.
- `onResolveHold(holdId)` → `kind: "resolve"`, `loaded`.
- `onReviewHold(holdId)` → `draftFromHold`로 `orderOpened`(null이면 아무것도 안 함). 탭은 옮기지 않는다(카드가 모든 탭에 뜬다).
- `onSaveAutoOrder(itemId, request: AutoOrderRequest)` → `kind: "save", form: "auto"`.
- `onOpenOrders()` → `onTab("orders")`와 같다(주문 결과 안내의 버튼).
- 새 양식 편집은 기존 `onEdited(form)`(`receipt`·`auto`).

- [ ] handlers 테스트(요청 본문, 같은 초안을 두 번 보내면 같은 request_id, repriced일 때만 unit_price, canSubmit 아니면 요청 없음) → 구현 → 커밋 "재고 화면 2: 주문·입고·보류·자동 주문 핸들러".

### Task 4: 화면 부품과 연결

**Files:** 새 `screens/inventory/OrderProposal.tsx`, `OrderConfirm.tsx`, `OrdersScreen.tsx`, `AutoOrderScreen.tsx`, Modify `StockScreen.tsx`, `inventory/view.tsx`(탭 화면 분기·주문 확인 카드·결과 안내), `styles/inventory.css`, 테스트 `inventory/view.test.tsx`(또는 새 `inventory/orders.view.test.tsx`).

- `OrderProposal`(현황 요약 아래): 묶음이 없으면 그리지 않는다. 제목 '부족한 구매 품목', 거래처 카드마다 품목·제안량·단가, '주문 확인' 버튼(요청 중이면 막음).
- `OrderConfirm`(탭 줄 아래, `order !== null`일 때): 제목 '주문 확인: {거래처}', 새 단가면 안내 '거래처가 알려 준 새 단가로 주문해요', 줄마다 품목·수량 입력(`aria-label="{품목} 주문 수량({단위})"`)·단가·금액·'빼기', 예상 총액('예상 총액 n원(실제 금액은 주문 뒤 확인)'), 배송지(없으면 경고 '배송지를 먼저 설정해 주세요' + 품목·기준 탭으로 가는 버튼), '주문하기'(`canSubmit` 아니거나 요청 중이면 막음, 주문 중이면 '주문 중…')·'취소'.
- 결과 안내(`orderResult !== null`): `role="status"` 안내 글 + '주문·입고 보기' + '닫기'.
- `OrdersScreen`: 위에 '보류' 묶음(없으면 '보류된 일이 없어요'): 줄마다 품목·사유·날짜·새 단가, 버튼 '새 단가로 다시 주문'(canReview)·'다시 확인'(canRefresh, 보류 주문 재조회)·'해결로 표시'. 아래 '주문' 목록(없으면 '주문이 없어요'): 카드마다 거래처·출처·상태 배지·날짜·총액, 줄(주문·입고·남은 수량), '다시 확인'(canRefresh, '확인 중…'), 입고 양식(canReceive: 줄마다 입고 수량 입력 — 남은 수량으로 시작, 남은 수량 0인 줄은 빼고 — 과 '이미 마감에서 셌어요' 체크, '입고 저장'; 수량이 모두 비었거나 숫자가 아니면 막음. 빈 칸 줄은 보내지 않는다).
- `AutoOrderScreen`: 배송지가 없으면 경고. 표(DataTable): 품목·자동 주문(켜짐/꺼짐)·한도·최근 결과·선택 버튼(주문 불가면 막고 사유). 고른 품목의 편집 카드: '자동 주문 켜기' 체크, 켤 때 동의 체크('부족할 때 하루 마감 직후 이 한도 안에서 자동으로 주문하는 데 동의해요'), 1회 한도·월 한도(원) 입력, '저장'. 켜기 + 동의 안 함이면 저장을 막는다. 한도 입력은 금액 글(`/^\d+(\.\d{1,2})?$/`). 처음 값: 설정이 있으면 그 값, 없으면 1회 100000·월 300000(빈 칸이 아니라 시작값 — 서버가 필수로 받는다).
- 탭 화면 모두 요청 중엔 입력·버튼을 막는다(화면 1과 같은 규칙).
- CSS는 `inventory.css`에(토큰만), 좁은 폭에서 줄바꿈(화면 1의 `inv-wrap`·카드 규칙 재사용).

- [ ] 렌더 테스트(제안 없음/있음, 주문 확인: 막힘·배송지 경고·새 단가 안내·주문 중, 결과 안내 문구 3종, 보류 버튼 조건, 주문 카드: 재조회·입고 양식 조건·남은 0 줄 제외, 자동 주문: 사유·동의 없으면 저장 막힘) → 구현 → 커밋 "재고 화면 2: 주문·입고·보류·자동 주문 화면".

### Task 5: 미리보기 프레임

**Files:** `preview/fixtures.ts`, `preview/frames.tsx`, 테스트(기존 프레임 테스트가 id 유일성·data-screen을 확인하면 그대로 통과).

- 픽스처에 주문(접수·일부 입고·불명·거절)·보류(가격 변동 새 단가·한도 초과·접수 불명)·자동 주문 설정(켜짐 1·꺼짐 1·주문 불가 1)을 더한다.
- 프레임: `inventory-stock-proposal`(제안 묶음), `inventory-order-confirm`(주문 확인 카드), `inventory-order-repriced`(새 단가 초안), `inventory-order-result`(결과 안내), `inventory-orders`(보류·주문·입고 양식), `inventory-orders-empty`, `inventory-auto`(목록), `inventory-auto-edit`(편집 카드 — 편집 카드를 고른 상태로 그릴 수 있게 `AutoOrderScreen`이 처음 고른 품목을 props `initialItemId?`로 받는다. 앱은 넘기지 않는다).
- 데스크톱·모바일 두 크기(기존 `inventoryFrame` 방식).

- [ ] 커밋 "재고 화면 2: 미리보기 프레임".

### Task 6: 인수 테스트 TC9와 테스트 케이스 문서

**Files:** 새 `backend/tests/acceptance/test_tc9_inventory.py`(필요하면 `flow.py`에 재고 도움 함수), `docs/test-cases.yaml`, `docs/TEST-CASES.xlsx`(스크립트로 생성).

사용자가 API로 하는 순서를 그대로 따라간다(`/api/v1/inventory`, `tests/conftest.py`의 `api_client`, Mock 거래처). 테스트 이름은 `test_tc9_{n}_{한국어_제목}`.

- TC9-1 등록 → 마감 → 부족: 거래처·품목 일괄 등록(현재 수량 포함), 기준 저장, 하루 마감으로 수량을 줄이면 상태 `short`와 제안 주문량(구매 단위로 올림), 미입력 품목은 `uncounted`(0이 아님).
- TC9-2 수동 주문은 같은 request_id로 두 번 보내도 한 번만: 배송지 설정, 주문 → 접수·배송 중 수량, 같은 요청 다시 → 같은 주문 id, 주문 수 1.
- TC9-3 일부 입고와 '이미 마감에서 셌어요': 일부 입고 → `partially_received`·보유 증가, 남은 수량을 `already_counted`로 입고 → `received`·보유 그대로, 남은 수량 초과 입고 422.
- TC9-4 자동 주문은 마감 직후 한 번, 같은 품목 접수 불명이면 보류: 자동 주문 켜기(동의) → 마감으로 부족 → `auto_orders`에 접수 1, 거래처를 `unknown_then_accept`로 바꾼 다른 품목은 접수 불명 + 보류, 마감을 다시 해도 접수 불명 품목은 다시 주문하지 않음.
- TC9-5 보류 재조회와 해결: 접수 불명 주문 재조회 → 접수, 그 보류가 풀림. 가격 변동 거래처 주문 → 거절 + 보류(새 단가), 새 단가로 다시 주문(`unit_price`) → 접수, 보류 해결 → 미해결 보류 0.
- TC9-6 한도 초과는 줄여 주문하지 않고 보류: 1회 한도보다 큰 자동 주문 → 주문 없음, 보류 `limit_exceeded`.
- `docs/test-cases.yaml`에 group `TC9`, item '재고 관리(주문·입고·자동 주문)', 케이스마다 precondition·steps·expected·`method: 자동`·`tests:`(테스트 경로::이름). `tests/test_test_cases_doc.py`가 위치·엑셀 행을 확인한다.
- `uv run --directory backend python ../scripts/test_cases.py run`으로 엑셀 갱신(실패가 있으면 종료 코드 1).

- [ ] 테스트(백엔드 코드를 바꾸지 않으므로 처음부터 통과해야 한다 — 실패하면 테스트 흐름이 틀렸거나 실제 버그다. 버그면 멈추고 보고) → YAML → 엑셀 → `uv run --directory backend pytest -q` → 커밋 "재고 인수 테스트 TC9와 테스트 케이스 문서".

### Task 7: 문서·WBS

- `CLAUDE.md` 재고 프론트 줄에 주문 초안(`order`, 멱등 `request_id`를 다시 시도까지 지킨다)·탭 `orders`·`auto`, `orderModel.ts`, 주소 목록에 `#/inventory/orders`·`#/inventory/auto`.
- `docs/HANDOFF.md`: main 줄(#44 머지 여부에 따라), 테스트 수, 지금 상태 '재고 화면 2 | #45 | …', 다음 할 일(디자이너 와이어프레임, 미룬 작은 것), TC 문서 행 수.
- WBS: `wbs.py set 4.15 --status 완료 --start 2026-11-08 --end 2026-11-08 --pct 1 --output "PR #45"`, `date 2026-11-08`.
- 전체 테스트·빌드 → 커밋 "재고 화면 2: 문서·WBS".
