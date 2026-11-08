# 재고 화면 1(현황·하루 마감·품목·기준) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 왼쪽 메뉴 '재고'로 들어가 재고 현황을 보고, 하루 마감(실사 입력 → 이상 수량 확인 → 저장, 자동 주문 결과 요약)을 하고, 품목·거래처·보충 기준(AI 추천 포함)·설정을 고칠 수 있다. 디자인은 나중에 받으므로 기존 토큰·뼈대로 만든 기능 화면이다.

**Architecture:** 재고는 코칭과 상태를 섞지 않는다. 코칭 앱 상태(`app/state.ts`)는 주소(`Route`)만 안다: 주소가 `inventory`면 `App`이 `InventoryApp`(자기 `useReducer`)을 그린다. 재고 쪽 구조는 코칭과 같은 모양으로 `api/inventory.ts`(호출) → `inventory/state.ts`(순수 reducer, 요청 번호로 늦은 응답 버림) → `inventory/screenModel.ts`(행·버튼·문구, 순수) → `screens/inventory/*`(props만). 뼈대(`AppShell`·`Rail`·`Header`)는 그대로 쓴다. 새 공용 부품은 `components/DataTable` 하나(뼈대 폭이 좁으면 카드 목록).

**Tech Stack:** React 19, TypeScript, Vite, vitest + @testing-library/react, openapi-fetch(생성 타입 `api/schema.d.ts`).

**설계:** `docs/superpowers/specs/2026-11-08-inventory-design.md` 5장(API)·6장(화면)·8장. IA 원본 `design/2026-11-05-ia-inventory-proposal/AX_IA.md`의 S01~S05(화면 이름·흐름 참고, 시각 디자인은 없음).

## Global Constraints

- 모든 명령은 저장소 루트에서: `npm --prefix frontend test`, `npm --prefix frontend run build`. 백엔드는 이 PR에서 바꾸지 않는다(바꾸면 `uv run --directory backend pytest`).
- TDD: 순수 함수(routes·shell·reducer·screenModel·필터)는 먼저 실패하는 테스트. 화면 부품은 @testing-library로 렌더 테스트.
- 코드 품질(`CLAUDE.md`): 판단은 순수 함수, 상태 변경은 reducer 한 곳, 컴포넌트는 props만(부품 안에서 끝나는 UI 상태만 부품이 가진다), 제어 플래그 인자 금지, 필요한 값만 넘긴다.
- 백엔드 호출은 `frontend/src/api/inventory.ts`만 한다(경로 문자열은 여기에만). `api/client.ts`의 `api`(X-Client-Id 붙음)·`toOutcome`을 쓴다. 타입은 `api/types.ts`에 `Schemas[...]` 별칭으로 더한다. `schema.d.ts`는 손대지 않는다.
- 주소를 읽고 만드는 곳은 `lib/routes.ts`의 `parseRoute`·`toHash`뿐이다.
- 색·글자 크기·폭·선·모서리는 `styles/tokens.css`의 `var(--…)`만(`tokens.test.ts`가 검사). 새 CSS는 `styles/inventory.css` 한 파일(main.tsx·preview에서 불러오기).
- 수량·금액은 API에서 문자열(Decimal)로 온다. 화면은 문자열을 그대로 보이고(필요하면 `lib/inventory/format.ts`에서 천 단위 쉼표), 계산은 하지 않는다. 계산은 서버가 준 값(`on_hand`·`in_transit`·`status`·`suggested_quantity`)을 쓴다. **미입력(`on_hand: null`)은 0이 아니다** — '미입력'으로 보인다.
- 사용자에게 보이는 문구는 한국어. 오류는 서버의 `detail` 문장을 알림(`Toast`)으로.
- 저장 중엔 그 버튼을 막고 '저장 중…', 실패하면 입력을 둔 채 알림. 저장하지 않은 입력이 있으면 재고 탭을 옮길 때 `window.confirm`으로 확인(재고 화면 안에서만, 확인 함수는 주입받아 테스트한다).
- 커밋 메시지는 한국어, AI 공동저자·생성 표기 금지. 브랜치 `task/44-inventory-screens-1`. 푸시는 마지막에 사용자 요청으로.

## File Structure

| 파일 | 할 일 |
|---|---|
| Modify `frontend/src/lib/routes.ts` (+test) | `Route`에 `{ name: "inventory"; tab: InventoryTab }`, `InventoryTab = "stock" \| "close" \| "items"`. `#/inventory`→stock, `#/inventory/close`, `#/inventory/items`. `contextOf`→`"inventory"` |
| Modify `frontend/src/lib/shell.ts` (+test), `layout/icons.tsx`, `layout/Rail.tsx` | `NavKey`에 `"inventory"`(라벨 '재고', 아이콘 `InventoryIcon`), `railActive(inventory)`→`"inventory"`, `routePhase`→null |
| Modify `frontend/src/app/handlers.ts`, `app/screenModel.ts`, `app/load.ts`, `app/view.tsx` | 메뉴 '재고' 누르면 `#/inventory`. 코칭 쪽은 inventory 주소에서 불러올 것이 없고(그 외 공통 `tasks`도 불필요하면 부르지 않게) 그리지도 않는다 |
| Modify `frontend/src/app/App.tsx` | `state.route.name === "inventory"`면 `<InventoryApp tab=… rail=…/>`(코칭 `AppView` 대신) |
| Create `frontend/src/api/inventory.ts` (+test), Modify `api/types.ts` | 재고 API 호출 함수 전부(이 PR이 쓰는 것 + 다음 PR용 주문·입고·보류·자동 주문도 미리) |
| Create `frontend/src/inventory/state.ts` (+test) | 재고 reducer |
| Create `frontend/src/inventory/screenModel.ts` (+test), `frontend/src/lib/inventory/format.ts` (+test) | 탭별 화면 모델, 필터, 라벨·숫자 표시 |
| Create `frontend/src/inventory/requests.ts` (+test) | 요청 번호를 붙여 실행(`createRunner`처럼), 성공 응답 → action |
| Create `frontend/src/inventory/InventoryApp.tsx` | `useReducer` + 불러오기 effect + handlers → `InventoryView` |
| Create `frontend/src/inventory/view.tsx` (+test) | `InventoryView`: `AppShell` + 탭 줄 + 탭별 화면 |
| Create `frontend/src/components/DataTable.tsx` (+test) | 열 정의로 그리는 표, 좁으면 카드 목록 |
| Create `frontend/src/screens/inventory/StockScreen.tsx`, `CloseScreen.tsx`, `ItemsScreen.tsx` (+ 부품) | S04, S05(+check·결과), S01·S02·S03·설정 |
| Create `frontend/src/styles/inventory.css` | 탭 줄·표·카드·폼 배치(토큰만) |
| Modify `frontend/src/preview/frames.tsx`, `preview/fixtures.ts` | 재고 프레임(`data-screen="inventory-…"`) |
| Docs | `CLAUDE.md`(구조: 프론트 재고), `docs/HANDOFF.md`, `docs/WBS.xlsx` 4.14 |

---

### Task 1: 주소·왼쪽 메뉴·앱 연결(빈 재고 화면까지)

**Files:** `lib/routes.ts`·`lib/routes.test.ts`, `lib/shell.ts`·테스트, `layout/icons.tsx`, `layout/Rail.tsx`, `app/handlers.ts`·테스트, `app/load.ts`·테스트, `app/screenModel.ts`, `app/view.tsx`, `app/App.tsx`, 새 `inventory/InventoryApp.tsx`(이 태스크에서는 뼈대 + "재고" 제목만 그리는 자리 부품).

**Interfaces (Produces):**
- `export type InventoryTab = "stock" | "close" | "items";` (`lib/routes.ts`) — 다음 PR이 `"orders" | "auto"`를 더한다.
- `Route`에 `{ name: "inventory"; tab: InventoryTab }`. `INVENTORY_TABS: readonly InventoryTab[]`(탭 순서).
- `parseRoute("#/inventory")` → `{name:"inventory",tab:"stock"}`, `"#/inventory/close"` → close, `"#/inventory/items"` → items, `"#/inventory/zzz"` → HOME. `toHash`는 stock이면 `#/inventory`, 그 밖은 `#/inventory/{tab}`(왕복 테스트).
- `contextOf(inventory)` → `"inventory"`. `isListRoute`는 false.
- `NavKey = "home" | "work" | "documents" | "inventory"`, 라벨 '재고', 순서는 결과물 다음. `railActive` → `"inventory"`, `routePhase` → null.
- `Handlers.navigate("inventory")` → 주소 `{name:"inventory",tab:"stock"}`.
- 코칭 `needsLoad`: inventory 주소면 null(코칭 데이터를 부르지 않는다). 코칭 `screenModel`은 inventory 주소에서 `{ kind: "loading" }`을 내도 되지만 `App`이 그 경우 `AppView`를 그리지 않는다.
- `InventoryApp` props: `{ tab: InventoryTab; rail: RailProps; onTab: (tab: InventoryTab) => void }`(rail은 App이 코칭 handlers의 navigate로 만든다 — `app/view.tsx`가 rail props를 만드는 함수를 이미 갖고 있으면 그것을 내보내 재사용).

- [ ] 실패 테스트: routes(파싱·toHash 왕복·contextOf), shell(railItems에 재고, railActive, routePhase), handlers(navigate inventory), load(inventory → null).
- [ ] 구현, `App.tsx`에서 분기. 이 단계의 `InventoryApp`은 `AppShell` 안에 `<h1>재고</h1>`만.
- [ ] `npm --prefix frontend test`·`build` 통과 → 커밋 "재고 메뉴·주소와 앱 연결".

### Task 2: 재고 API 모듈과 타입

**Files:** 새 `api/inventory.ts`·`api/inventory.test.ts`, `api/types.ts`.

**Interfaces (Produces)** — 모두 `Promise<ApiResult<T>>`, 경로는 `/api/v1/inventory…`:
- `getInventory(): InventoryView`
- `addItems(items: ItemDraft[]): InventoryView` (`POST /items/bulk`, 본문 `{items}`), `addItem(item: ItemDraft): InventoryView` (`POST /items`), `updateItem(itemId, patch: ItemPatch): InventoryView`
- `addSupplier(draft: SupplierDraft)`, `updateSupplier(supplierId, patch: SupplierPatch)` → InventoryView
- `setSettings(body: InventorySettingsRequest)`, `setPolicy(itemId, body: ReorderPolicyRequest)` → InventoryView
- `checkClose(body: CloseCheckRequest): CloseCheckView`, `recordClose(body: CloseRequest): CloseView`
- `suggestPolicy(itemId)`, `applySuggestion(itemId)` → InventoryView
- (다음 PR용, 지금 함께) `placeOrder(body: OrderRequest): OrderView`, `refreshOrder(orderId): OrderView`, `receive(orderId, body: ReceiptRequest): OrderView`, `resolveHold(holdId): InventoryView`, `setAutoOrder(itemId, body: AutoOrderRequest): InventoryView`
- `api/types.ts`: 위 요청·응답 타입과 `ItemView`, `InventoryItem`(=`Item`), `Supplier`, `ReorderPolicy`, `InventorySettings`, `Close`, `Anomaly`, `AnomalyKind`, `StockStatus`, `ItemKind`, `Procurement`, `MockOutcome`, `Order`, `Hold`, `HoldReason`, `OrderStatus`, `AutoOrderSetting`, `AutoOrderOutcome`, `PolicySuggestion` 별칭(이름은 `schema.d.ts`의 components 이름을 확인해 그대로. `-Input/-Output` 이름은 없다).
- 테스트: `coaching.test.ts`처럼 `api`를 가짜 fetch로 바꿔 경로·메서드·본문을 확인(대표 6개 이상: get, bulk, policy PUT, check, close, suggestion).

- [ ] 실패 테스트 → 구현 → 통과 → 커밋 "재고 API 호출 모듈".

### Task 3: 재고 reducer와 요청 실행

**Files:** 새 `inventory/state.ts`·`state.test.ts`, `inventory/requests.ts`·`requests.test.ts`.

**State:**
```ts
export type InventoryState = {
  view: InventoryView | null;          // 마지막으로 받은 재고 전체
  loadFailed: boolean;                  // 처음 불러오기 실패(다시 시도 버튼)
  inflight: { seq: number; kind: InventoryCall } | null; // 지금 기다리는 요청 하나
  toast: string | null;
  filter: { query: string; kind: ItemKind | "all" };     // 현황·마감 공용 검색·분류
  close: {                              // 하루 마감 입력
    counts: Record<string, string>;     // 품목 id → 입력 글(빈칸 = 미입력)
    check: CloseCheckView | null;       // 검사 결과(이상 수량)
    confirmed: string[];                // 이상 수량을 '맞아요'로 확인한 품목
    adjustments: Record<string, { delta: string; reason: string }>;
    result: CloseView | null;           // 저장 결과(자동 주문 요약)
  };
  dirty: boolean;                       // 저장하지 않은 입력이 있다(탭 옮길 때 확인)
};
export type InventoryCall = "load" | "save" | "check" | "close" | "suggest";
```
**Actions (예):** `requested{seq,kind}`, `failed{seq,message}`, `loaded{seq,view}`(현황 갱신·inflight 해제), `checked{seq,check}`, `closed{seq,result}`(입력 비움·dirty false·view 갱신), `filterChanged`, `countChanged{itemId,text}`(dirty true, check 무효화), `anomalyConfirmed{itemId,confirmed}`, `adjustmentChanged{itemId,delta,reason}`, `closeReset`, `edited`(폼에 입력 생김 → dirty), `saved`(dirty false), `toastClosed`.
- 번호가 다른 응답은 버린다(`inflight?.seq !== seq`면 state 그대로). `failed`는 입력을 지우지 않는다.
- `inventory/requests.ts`: `createInventoryRunner(dispatch)` — 코칭 `app/requests.ts`의 `createRunner`와 같은 원리(번호 증가, `toOutcome`, 예외면 `BACKEND_UNREACHABLE`). `done: (data, seq) => InventoryAction`.

- [ ] reducer 표 형태 테스트(늦은 응답 버림, 실패 시 입력 유지, 마감 저장 후 입력 비움, 수량 바꾸면 check 무효), runner 테스트 → 구현 → 커밋 "재고 상태(reducer)와 요청 실행".

### Task 4: 화면 모델·표시 함수

**Files:** 새 `inventory/screenModel.ts`·테스트, `lib/inventory/format.ts`·테스트.

**Interfaces:**
- `format.ts`: `quantityText(q: string | null, unit: string): string` → null이면 `"미입력"`, 아니면 `"1,234.5 m"`(천 단위 쉼표, 소수 그대로), `moneyText(m: string): string` → `"12,000원"`, 라벨 상수 `KIND_LABELS`(finished 완제품·material 재료·packaging 포장재), `STATUS_LABELS`(uncounted 미입력·short 부족·in_transit 배송 중·ok 충분), `PROCUREMENT_LABELS`(purchase 구매·make 직접 제작), `ANOMALY_LABELS`.
- `filterItems(items: ItemView[], filter): ItemView[]` — 숨긴(archived) 품목 제외, 이름·옵션 부분 일치(대소문자·앞뒤 공백 무시), 분류.
- `stockModel(view, filter)` → `{ rows: StockRow[]; shortCount: number; uncountedCount: number; lastClose: string | null }`. `StockRow = { itemId, name, option, kind, onHand, inTransit, status, statusLabel, suggested }`(문자열로 다 만든 값). 부족(short) 먼저, 그다음 미입력, 그다음 이름순.
- `closeModel(view, closeState, filter)` → 행(품목·지난 수량·입력 칸 값), 검사 결과 행(이상 수량: 품목·종류 라벨·지난→입력·확인 여부·조정), `canCheck`(입력이 하나라도), `canSave`(검사했고 모든 이상 수량이 확인되었거나 조정되었을 때 — 서버 규칙 `confirmed` 참고), 저장 결과 요약(`auto_orders`를 '주문 n건·보류 n건' 문장과 행으로).
- `itemsModel(view)` → 품목 행(편집 대상), 거래처 목록, 설정, 품목별 기준·추천(추천은 '확인 전' 라벨과 이유).

- [ ] 표 형태 테스트(미입력≠0, 정렬, 필터, canSave 경계, 자동 주문 요약 문장) → 구현 → 커밋 "재고 화면 모델과 표시 함수".

### Task 5: DataTable과 재고 CSS

**Files:** 새 `components/DataTable.tsx`·테스트, `styles/inventory.css`, `main.tsx`·`preview/main.tsx`(CSS 불러오기).

**Interface:** `DataTable<Row>({ caption, columns: { key: string; header: string; cell: (row: Row) => ReactNode; align?: "start" | "end" }[], rows: Row[], rowKey: (row: Row) => string, empty: string })`. 넓으면 `<table>`(caption은 시각적으로 숨김 가능), 좁으면(`@container app` 폭 규칙, 기존 `layout.css`의 기준값을 따른다) 같은 마크업을 CSS로 카드 목록처럼(각 셀 앞에 `data-label`로 머리글) 보인다. 행이 없으면 `empty` 문장.
- 테스트: 머리글·셀·빈 문장·`data-label`.
- CSS: 탭 줄(`.inv-tabs`), 표(`.data-table`), 숫자 오른쪽 정렬, 상태 배지(부족은 강조색 토큰). 토큰만.

- [ ] 테스트 → 구현 → 커밋 "DataTable과 재고 화면 CSS".

### Task 6: 화면 부품(현황·하루 마감·품목·기준)

**Files:** 새 `screens/inventory/StockScreen.tsx`, `CloseScreen.tsx`, `ItemsScreen.tsx`(필요하면 `ItemForm.tsx`·`PolicyForm.tsx`·`SupplierForm.tsx`·`SettingsForm.tsx`), `inventory/view.tsx`(InventoryView: AppShell + 탭 줄 + 탭 화면), 테스트 `screens/inventory/*.test.tsx`·`inventory/view.test.tsx`.

화면은 props(화면 모델 + 콜백 + busy)만 받는다. 폼 입력 중 값처럼 부품 안에서 끝나는 상태만 부품이 가진다(저장 성공하면 부모가 새 view를 주고 폼은 그 값으로 다시 시작: `key`로 초기화).
- **S04 현황(StockScreen):** 위에 요약('부족 n개 · 미입력 n개 · 마지막 마감 날짜'), 검색 칸·분류 선택, DataTable(품목·옵션·종류·보유·배송 중·상태·제안 주문량). 품목이 하나도 없으면 '품목·기준' 탭으로 가는 버튼이 있는 빈 화면. '하루 마감 하기' 버튼(→ close 탭). 부족 품목 주문(S06·S07)은 다음 PR — 지금은 제안 주문량만 보인다.
- **S05 하루 마감(CloseScreen):** 마감 날짜(기본 오늘, `<input type="date">`), 검색·분류, 품목마다 '지난 수량'과 실사 입력 칸(빈칸 = 미입력, 안내 문장 "비워 두면 미입력으로 남아요(0이 아니에요)"). '검사' → 이상 수량 패널(S05-check): 행마다 '맞아요'(확인) 또는 조정(±수량·사유 필수). '마감 저장'(canSave일 때만) → 결과 패널: 저장한 날짜, 자동 주문 요약(주문·보류 행), '재고 현황 보기'.
- **품목·기준(ItemsScreen):**
  - S01 일괄 등록: 여러 줄 입력 표(이름·옵션·종류·단위·조달·거래처·현재 수량, 줄 추가/빼기, 최대 200) → 등록.
  - S02 품목 편집: 품목 선택 → 이름·옵션·종류·단위(원장 기록이 있으면 잠김: 서버가 422로 막으므로 실패 알림으로 충분, 화면은 안내 문장)·조달·거래처·숨기기.
  - 거래처: 추가·이름 바꾸기·모의 결과(`mock_outcome`, 라벨 '모의 거래처 응답: 접수/가격 변동/품절/접수 불명 뒤 접수').
  - S03 보충 기준: 최소·목표·구매 단위·배송 기간·단가 → 저장. 'AI 추천 받기'(요청 중 '추천 받는 중…') → 추천(확인 전: 최소·목표·구매 단위·이유) → '추천 적용'.
  - 설정: 배송지·이상 수량 비율·오래된 실사 일수.
- `InventoryView({ tab, model, busy, on, rail, mainId? })` — `on`은 `InventoryHandlers`(타입을 `inventory/view.tsx`에서 내보낸다). 탭 줄은 `role="tablist"`가 아니라 링크 모양 버튼 목록(`aria-current`).

- [ ] 부품마다 렌더 테스트(미입력 표시, 빈 화면, 검사 전 저장 막힘, 추천 '확인 전' 표시, 조정 사유 없으면 확인 막힘) → 구현 → 커밋(화면별로 나눠도 된다).

### Task 7: InventoryApp 연결과 미리보기 프레임

**Files:** `inventory/InventoryApp.tsx`, 새 `inventory/handlers.ts`·테스트, `preview/fixtures.ts`, `preview/frames.tsx`, `preview/handlers.ts`(재고 NOOP).

- `InventoryApp`: `useReducer(inventoryReducer, initial)`, 처음 들어오면 `getInventory`(실패하면 다시 시도 화면), `makeInventoryHandlers({ state, run, dispatch, confirmLeave })`가 버튼을 요청·action으로 바꾼다(코칭 `app/handlers.ts`와 같은 모양). 탭 이동은 `dirty`면 `confirmLeave()`(App이 `window.confirm`을 넘긴다)가 true일 때만. 알림은 `Toast`(3.5초 뒤 닫힘, 코칭과 같은 시간 상수 재사용).
- 마감 저장의 `close_date`는 입력 날짜, `counts`는 빈칸을 뺀 입력(문자열 그대로), `confirmed`·`adjustments`(delta·reason).
- 미리보기: 재고 픽스처(생성 타입으로: 품목 6개 — 부족·미입력·배송 중·충분·제작품·숨김, 거래처 2, 기준·추천, 마지막 마감, 검사 결과에 이상 수량 2개, 마감 결과에 자동 주문 주문 1·보류 1). 프레임: `inventory-stock`, `inventory-stock-empty`, `inventory-close`, `inventory-close-check`, `inventory-close-result`, `inventory-items`(데스크톱·모바일 — 기존 `frame()`처럼 `FRAME_SIZES` 둘 다), 각 프레임 루트에 `data-screen="inventory-…"`. `frames.test.tsx`의 기존 검사(모든 프레임 렌더·id 중복 없음)를 통과.
- 테스트: handlers(탭 이동 확인, 마감 저장 본문, 추천 요청), 프레임 렌더.

- [ ] 테스트 → 구현 → 커밋 "재고 앱 연결과 미리보기 프레임".

### Task 8: 문서·WBS

- `CLAUDE.md` 구조에 프론트 재고 줄: `frontend/src/inventory/`(InventoryApp·state·screenModel·handlers·requests, 코칭 상태와 분리, 주소 `#/inventory[/close|/items]`), `api/inventory.ts`, `screens/inventory/`, `components/DataTable`, `styles/inventory.css`, 미리보기 `inventory-*` 프레임.
- `docs/HANDOFF.md`: 기준일, main 줄(`7f51326`, PR #43까지, 이 PR이 #44), 테스트 수, 지금 상태 행 '재고 화면 1 | #44 | …', 다음 할 일(재고 화면 2: 주문·입고·보류·자동 주문, 인수 테스트·TC 문서).
- WBS: `uv run --no-project --with openpyxl python scripts/wbs.py set 4.14 --status 완료 --start 2026-11-08 --end 2026-11-08 --pct 1 --output "PR #44"`, `date 2026-11-08`.
- `npm --prefix frontend test`·`build`, `uv run --directory backend pytest -q` 통과 → 커밋 "재고 화면 1: 문서·WBS".
