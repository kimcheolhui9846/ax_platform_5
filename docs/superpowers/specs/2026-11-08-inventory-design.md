# 재고 관리(S) 설계

- 날짜: 2026-11-08
- 근거: `design/2026-11-05-ia-inventory-proposal/AX_IA.md` 03장(S01~S11), 01장 소융 구조도의 '재고 관리 S'
- 범위: 재고 관리 기능만. 작가 제안서(J)와 기존 구조 확장(P·G·A)은 따로 설계한다.
- 디자인: 받은 IA 문서에는 시안이 없고(배치 설명만 있다) 피그마 원문은 비공개다. 와이어프레임은 기능을 더 발전시킨 뒤 받기로 했으므로 **기능을 먼저 만들고 디자인은 나중에 입힌다.** 화면은 지금 토큰·뼈대로 동작하는 최소 형태로 두고 `/preview` 프레임으로 디자이너에게 넘긴다.

## 결정 사항

| 질문 | 결정 | 이유 |
|---|---|---|
| 주문은 무엇인가 | 모의 거래처 어댑터 `SupplierProvider`(기본 Mock) | 비용 0. S10 접수 불명·재조회·중복 방지와 S08 자동 주문을 실제처럼 만들고 테스트할 수 있다. 실제 거래처는 어댑터 하나만 바꾼다(AI 제공자와 같은 방식) |
| AI의 역할 | 보충 기준 추천 하나. 계산·판정은 모두 코드 | 명세: 계산은 코드, AI가 주문 권한을 결정하지 않음, 추천은 사용자가 확인 후 적용. 하네스의 가정≠사실 원칙과 같다 |
| 재고는 어디에 속하나 | owner마다 재고 묶음 하나, 왼쪽 메뉴 '재고' | 프로젝트(P)가 아직 없다. 저장소 호출이 묶음 키 하나를 받게 해 두면 나중에 `project_id`를 붙이기 쉽다 |
| 제작품과 재료 | 품목은 서로 독립(BOM 없음). 품목마다 조달 방식(구매·직접 제작) | 명세 범위. 재료는 하루 마감 실사로 맞춘다 |
| 자동 주문 시점 | 하루 마감을 저장할 때 | 렌더 무료는 잠들어 예약 실행을 믿을 수 없다. 수량이 줄어드는 시점은 마감뿐이다 |
| 저장 방식 | 재고 묶음 하나 = JSON 문서 하나, 수량은 원장에서 계산 | 세션 저장과 같은 방식이라 요구가 바뀌어도 Pydantic 모델만 고친다(마이그레이션 없음). 1인 작가 규모에 충분하다. 원장이 커지면 그때 테이블로 뺀다 |

## 1. 데이터 모델 (`app/inventory/models.py`)

`InventoryState` 하나가 owner의 재고 전부다.

- `Item`: `item_id`, `name`, `option`(없을 수 있음), `kind`(`finished`·`material`·`packaging`), `unit`(개·m·g 등 자유 문자열), `procurement`(`purchase`·`make`), `supplier_id`(구매일 때), `archived`.
  - 원장 기록이 있으면 `unit`을 바꿀 수 없다(단위 혼용 방지, 422).
  - 수량은 모두 그 품목 단위의 `Decimal`(소수 둘째 자리까지, 음수 불가).
  - 삭제하지 않고 `archived`로 숨긴다(원장·주문 보존).
- `Supplier`: `supplier_id`, `name`, `kind`(지금은 `mock`), `mock_outcome`(Mock 거래처에만, 3장).
- `ReorderPolicy`(품목마다): `min_stock`, `target_stock`(≥ min), `purchase_unit`(> 0), `lead_days`, `unit_price`.
- `PolicySuggestion`(품목마다 최대 하나): AI가 낸 기준 값·이유. 화면에 "AI 추천 · 확인 전"으로 보이고 적용해야 기준이 된다.
- `LedgerEntry`(추가만, 고치지 않음): 공통 `entry_id`·`item_id`·`at`
  - `count`: 실사 수량. 하루 마감과 일괄 등록의 '현재 수량'
  - `adjust`: 더하기·빼기 값과 사유(필수)
  - `receipt`: 주문 id, 받은 수량, `already_counted`
- `Close`: `close_id`, 날짜, 품목별 실사 수량. 적지 않은 품목은 미입력이다(0이 아니다). 같은 날 다시 마감할 수 있고 나중 실사가 이긴다(원장에서 마지막 `count`).
- `Order`: `order_id`, `request_id`(멱등 키), 줄(품목·수량·단가), 총액, `origin`(`manual`·`auto`), `status`(`accepted`·`rejected`·`unknown`·`partially_received`·`received`), 거절 사유, 거래처 주문 번호, 받은 수량.
- `AutoOrderSetting`(품목마다): `enabled`, `consented_at`, `per_order_limit`, `monthly_limit`(금액). 처음엔 꺼짐.
- `Hold`: `hold_id`, 품목, 주문(있으면), 사유(`price_changed`·`limit_exceeded`·`out_of_stock`·`stale_count`·`unknown`), 현재 단가(가격 변동일 때), 생긴 시각, `resolved`.
- `InventorySettings`: 배송지, 이상 수량 기준(기본 감소율 50%), 오래된 재고 기준(기본 7일). 결제는 "거래처 계정 결제(모의)"로 표시만 한다.

## 2. 계산 규칙 (`app/inventory/rules.py`, 모두 순수 함수)

- **보유 수량** = 마지막 `count` + 그 뒤의 `adjust`·`receipt` 합. `already_counted` 입고는 더하지 않는다(중복 가산 방지). `count`가 없으면 미입력(`None`).
- **배송 중** = `accepted`·`partially_received` 주문의 (주문 수량 − 받은 수량) 합.
- **상태**: 미입력 / 부족(보유 + 배송 중 < 최소) / 배송 중 / 정상. 기준이 없으면 부족 판정을 하지 않는다.
- **제안 주문량** = (목표 − 보유 − 배송 중)을 구매 단위로 올림. 제작 품목은 주문 대신 '○ 제작 필요'.
- **이상 수량**: 음수는 거부. 입고 없이 직전 보유보다 늘었거나, 직전 보유 대비 기준(50%)보다 많이 줄었으면 '확인 필요'. 확인한 품목만 저장된다.
- **오래된 재고**: 마지막 실사가 기준(7일)보다 오래됐으면 자동 주문 대상에서 보류.
- **검색·분류 필터**는 프론트의 순수 함수다.

## 3. 거래처와 주문

**계약 `SupplierProvider`** (`app/inventory/supplier.py`)

- `place(request_id, lines, address) -> SupplierReply`, `lookup(request_id) -> SupplierReply`
- `SupplierReply`: 상태(`accepted`·`rejected`·`unknown`), 거절 사유(`price_changed`+현재 단가·`out_of_stock`), 거래처 주문 번호.
- 통신 오류·시간 초과는 예외가 아니라 `unknown`이다(주문이 들어갔을 수 있다). 다시 주문하지 않고 `lookup`으로만 확인한다.
- 설정 `SUPPLIER=mock`(기본)으로 고르고 `factory`가 만든다.

**Mock**: 비용 0, 저장 없이 결정적. 거래처의 `mock_outcome`이 결과를 정한다.

| `mock_outcome` | `place` | `lookup` |
|---|---|---|
| `accept`(기본) | 접수 | 접수 |
| `price_changed` | 거절(단가 +10%) | 거절 |
| `out_of_stock` | 거절(품절) | 거절 |
| `unknown_then_accept` | 접수 불명 | 접수 |

**수동 주문(S06 → S07)**: 제안에서 수량을 고친 뒤 확인하면 주문한다. 단가는 기준의 `unit_price`, 총액을 보여 준다. 배송지가 없으면 422. 거절·불명이면 주문 상태로 남기고 보류도 남긴다. 가격 변동 보류의 '직접 검토'는 현재 단가로 S07을 다시 연다.

**자동 주문**(하루 마감 저장 직후, 같은 잠금 안)

1. `plan_auto_orders(state, today)`(순수)가 자동 주문을 켜고 동의한 구매 품목마다 정한다.
   - 부족이 아니면 넘어감
   - 오래된 재고 → 보류 `stale_count`
   - 같은 품목에 `unknown` 주문이 있음 → 보류 `unknown`(중복 주문 방지)
   - 제안량 × 단가 > 1회 한도 → 보류 `limit_exceeded`(수량을 줄여 주문하지 않는다)
   - 이번 달 자동 주문 합계(`accepted`·`unknown`·입고 중) + 이번 금액 > 월 한도 → 보류 `limit_exceeded`
   - 그 밖에는 품목 하나에 주문 하나
2. `request_id = auto:{close_id}:{item_id}`. 같은 마감을 다시 보내도 주문이 두 번 나가지 않는다.
3. 거래처 응답을 주문 상태로, 거절·불명은 보류로 남긴다. 같은 품목·같은 사유의 미해결 보류는 하나만.
4. 마감은 주문 결과와 상관없이 저장된다.

자동 주문을 끄면 이후 실행만 멈추고 접수된 주문은 그대로다.

## 4. AI 기준 추천

- 기존 `LLMProvider`를 `response_model`(`PolicySuggestionOut`: 최소·목표·구매 단위·이유)로 부른다. 기본 Mock(비용 0, `mock_fill`).
- 입력: 품목 정보, 최근 실사·입고 기록에서 코드가 계산한 하루 평균 소진량, 배송 기간. 프롬프트는 `app/inventory/prompts/`에 두고 바깥 값은 `| inline`·`| block`으로 넣는다. 외부 전송 가림(`privacy.outbound_prompt`)을 거친다.
- 실패는 코칭과 같다: 제공자 실패 502, 자리 없음 503. 추천이 실패해도 기준은 바뀌지 않는다.
- 결과 검증: 목표 ≥ 최소, 구매 단위 > 0을 코드가 확인하고 어긋나면 `ProviderOutputError`처럼 다룬다.

## 5. API (`/api/v1/inventory`, `X-Client-Id`)

| 메서드·경로 | 화면 | 내용 |
|---|---|---|
| `GET /inventory` | S04·S06·S09·S10 | `InventoryView`: 품목별 보유·배송 중·상태·제안량/제작 필요·기준·추천·자동 주문 설정·마지막 실사, 주문, 보류, 거래처, 설정, 기준일 |
| `POST /inventory/items/bulk` | S01 | 여러 품목 등록, 현재 수량은 `count`. 전부 되거나 전부 안 됨 |
| `POST /inventory/items`, `PATCH /inventory/items/{id}` | S02 | 등록·수정·숨기기. 원장이 있는데 단위 변경은 422 |
| `POST /inventory/suppliers`, `PATCH /inventory/suppliers/{id}` | S02 | 거래처 |
| `PUT /inventory/settings` | 품목·기준 | 배송지·기준값 |
| `PUT /inventory/items/{id}/policy` | S03 | 기준 저장. 목표 < 최소는 422 |
| `POST /inventory/items/{id}/policy/suggestion` | S03 | AI 추천 받기(502·503) |
| `POST /inventory/items/{id}/policy/suggestion/apply` | S03 | 추천을 기준으로 |
| `POST /inventory/closes/check` | S05-check | 저장 없이 이상 수량 목록 |
| `POST /inventory/closes` | S05 | `{date, counts, adjustments, confirmed}`. 미확인 이상 수량이 있으면 422. 응답에 자동 주문 결과 |
| `POST /inventory/orders` | S07 | `{request_id, lines}`. 같은 `request_id`면 기존 주문을 돌려준다 |
| `POST /inventory/orders/{id}/refresh` | S10 | `lookup`으로 상태 갱신, 다시 주문하지 않음 |
| `POST /inventory/orders/{id}/receipts` | S11 | `{lines: [{item_id, quantity, already_counted}]}`. 남은 수량 초과는 422 |
| `POST /inventory/holds/{id}/resolve` | S10 | 직접 검토 완료 |
| `PUT /inventory/items/{id}/auto-order` | S08 | `{enabled, consent, per_order_limit, monthly_limit}`. 켤 때 동의·구매 거래처 필수(422) |

공통

- 바꾸는 요청은 owner별 잠금(`app/api/locks.py`와 같은 방식)으로 하나씩, 원자적으로(실패하면 저장하지 않음) 돈다.
- 오류 본문은 `{"detail": "<한국어>"}`, 문구는 `app/core/messages.py`. 경로마다 낼 수 있는 오류만 `error_responses(...)`로 적는다.
- 없는 품목·주문·보류·거래처는 404. 남의 재고는 보이지 않는다(owner가 곧 묶음 키).
- 응답 모델은 `ContractModel`을 상속한다(모든 속성 required).
- 라우터는 얇게(`app/api/inventory.py`), 상태 변경은 `app/inventory/service.py` 한 곳, 상태→응답은 `app/inventory/views.py`(순수).

**저장소**: `InventoryStore` 계약 `get(owner_id) -> InventoryState | None`·`save(state)`. memory·sqlite·postgres(테이블 `inventories(owner_id PK, updated_at, data JSONB)`) 세 구현, `build_storage`가 `STORE`로 함께 만든다.

## 6. 화면 (기능 먼저 버전)

- 왼쪽 메뉴에 '재고'. 주소는 `routes.ts`의 `parseRoute`·`toHash`에만 더한다.

| 업무 탭 | 주소 | 화면 |
|---|---|---|
| 재고 현황 | `#/inventory` | S04 표 + '부족 n개' → S06 제안 → S07 주문 확인(대화상자) |
| 하루 마감 | `#/inventory/close` | S05 입력(빈칸 = 미입력) → 검사 → S05-check 패널(확인·조정·사유) → 저장 결과(자동 주문 요약) |
| 주문·입고 | `#/inventory/orders` | S11 주문·남은 수량·입고('이미 마감에서 셌어요'), S10 보류(재조회·직접 검토·해결) |
| 자동 주문 | `#/inventory/auto` | S09 품목별 켜짐·꺼짐·최근 결과, 선택하면 S08 편집 패널 |
| 품목·기준 | `#/inventory/items` | S01 일괄 등록, S02 품목·거래처 편집, S03 기준 + AI 추천, 설정 |

- 재고 현황·하루 마감에 검색·분류 필터.
- 구조: `api/inventory.ts`(호출), `inventory/state.ts`(순수 reducer, 요청 번호로 늦은 응답 버림), `inventory/screenModel.ts`(행·버튼·문구, 순수), `screens/inventory/*`(props만). 코칭 상태와 섞지 않는다. 뼈대·오른쪽 패널은 그대로 쓴다.
- 새 부품은 `components/DataTable` 하나(뼈대 폭이 좁으면 카드 목록). 색·간격은 `tokens.css`만.
- 상태: 저장 중엔 버튼을 막고 '저장 중', 실패하면 입력을 두고 알림, 저장하지 않은 입력이 있으면 탭을 옮길 때 확인(재고 화면 안에서만).
- `/preview`에 S 화면 상태별 프레임(`data-screen="inventory-…"`).

## 7. 테스트

- `rules.py` 표 형태 테스트: 보유·중복 가산·미입력·올림·이상 수량·오래된 재고·`plan_auto_orders` 모든 사유와 한도 경계.
- 저장소 계약 `tests/test_inventory_store_contract.py`(memory·sqlite·postgres).
- Mock 거래처 네 결과와 재조회.
- API: 정상·404·422·남의 재고·같은 `request_id` 한 번·같은 마감 두 번이어도 자동 주문 한 번·실패 시 저장 없음.
- 인수 테스트 `tests/acceptance/`의 재고 TC(등록 → 마감 → 부족 → 수동 주문 → 일부 입고 → 자동 주문 → 보류 → 재조회), `docs/test-cases.yaml`·엑셀 행.
- 프론트: reducer·screenModel·필터·routes, `/preview` 프레임 렌더.

## 8. PR 나누기

| PR | 브랜치 | 내용 |
|---|---|---|
| #40 | `task/40-inventory-core` | 이 설계, 모델·규칙·저장소 3종·잠금, 품목·거래처·설정·기준·하루 마감 API, `GET /inventory` |
| #41 | `task/41-inventory-orders` | 모의 거래처, 수동 주문·재조회·입고·보류, 자동 주문, AI 기준 추천 |
| #42 | `task/42-inventory-screens-1` | 메뉴·주소·API 모듈·상태·DataTable, 재고 현황·하루 마감·품목·기준 화면 |
| #43 | `task/43-inventory-screens-2` | 주문·입고·보류·자동 주문 화면, `/preview` 프레임, 인수 테스트·TC 문서 |

PR마다 WBS(`scripts/wbs.py`)와 `docs/HANDOFF.md`를 같은 PR에서 고친다.

## 범위 밖

- 실제 거래처·결제·알림(푸시·메일) 연동, 예약 실행(크론), 제작 레시피(BOM), 프로젝트별 재고, 스토어 연동(X03).
- 명세가 "상세 보완 필요"로 둔 것(이상 수량 확인 상태 상세, 자동 주문 해제 확인 상태, 부분 입고·불량 구분 패널)은 이 설계의 최소 동작으로 만들고 와이어프레임을 받으면 다듬는다.
