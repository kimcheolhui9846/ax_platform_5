# AX 코칭 플랫폼 — 개발 기반(Foundation) 설계

- 작성일: 2026-10-15
- 근거 문서: `AX_코칭_플랫폼_기획_및_하네스_설계서.pdf`(이하 "설계서"), `AX Coaching Platform 기능 설계.pdf`(이하 "기능 설계")
- 범위: 본격 개발 전 준비 작업. 저장소 골격, 하네스 틀, API 계약, Mock 기반 개발 루프.

## 1. 배경과 전제

- 학교 수업 팀 프로젝트다. 개발(프론트·백엔드)은 한 명이 맡고, 디자인과 팀원이 피그마로 만든 UI flow 포함 프로토타입 HTML을 준다. 프론트는 그 디자인에 맞춰 만들고, 백엔드는 그 프론트에 맞춘다.
- **요구사항·디자인·하네스 모두 자주 바뀐다.** 모든 결정은 "바뀌었을 때 고칠 곳이 적은가"를 기준으로 한다.
- **비용을 아낀다.** 개발·테스트 루프는 API 키와 비용 없이 돌아가야 한다. 처음엔 Mock Provider만 쓰고, 품질 확인이 필요해지면 Claude API 어댑터를 추가한다.
- 핵심 자산은 **과제별 하네스**다. 사업계획·상품기획·브랜딩·마케팅 콘텐츠는 사용자가 원하는 결과물이 서로 다르므로, 하네스를 과제마다 따로 최적화한다.

## 2. 기술 스택

| 영역 | 선택 |
|---|---|
| 백엔드 | Python 3.12, FastAPI, Pydantic v2, uv(패키지·실행), Jinja2(프롬프트 템플릿), PyYAML |
| 테스트 | pytest, FastAPI TestClient |
| 프론트엔드 | React + Vite + TypeScript, npm |
| API 타입 | `openapi-typescript`로 백엔드 OpenAPI에서 타입 생성, 호출은 `openapi-fetch` |
| LLM | `LLMProvider` 인터페이스 + `MockProvider` (이후 `ClaudeProvider`) |
| 세션 저장 | `SessionStore` 인터페이스 + 메모리 구현 (이후 SQLite) |

## 3. 저장소 구조

```
ax_platform_5/
├── CLAUDE.md
├── docs/
│   ├── planning/              # 기획 PDF 사본 + 추출 텍스트
│   └── superpowers/specs/
├── design/                    # 디자인 HTML 원본, 받은 날짜별 폴더 (수정 금지, 누적 보관)
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py          # .env 설정 (PROVIDER=mock|claude 등)
│   │   ├── api/               # 라우터
│   │   ├── schemas/           # API 요청·응답 계약 (프론트 타입의 원본)
│   │   ├── core/              # 세션 상태 모델, SessionStore
│   │   ├── harness/
│   │   │   ├── base.py        # 공통 파이프라인
│   │   │   ├── policy.py      # policy.yaml 로딩·검증 모델
│   │   │   ├── registry.py    # task_type → 하네스 인스턴스
│   │   │   └── tasks/
│   │   │       ├── business_plan/
│   │   │       ├── product_planning/
│   │   │       ├── branding/
│   │   │       └── marketing_content/
│   │   └── providers/         # base.py, mock.py
│   └── tests/
└── frontend/
    ├── package.json
    └── src/
        ├── api/               # schema.d.ts(생성물) + client.ts
        ├── pages/
        └── components/
```

원칙:
- **계약의 원본은 `backend/app/schemas/` 하나다.** 프론트 타입은 `npm run gen:api`로 생성하고 손으로 고치지 않는다. 계약이 바뀌면 백엔드를 고치고 타입을 재생성하면, 어긋난 곳이 TS 컴파일 에러로 드러난다.
- **프론트 전용 Mock API는 만들지 않는다.** MockProvider로 도는 백엔드가 곧 Mock API다.
- **`design/`의 HTML은 원본 그대로 날짜별로 쌓는다.** 새 버전이 오면 직전 버전과 diff해 바뀐 화면만 React에 반영한다.

## 4. 하네스 설계

### 4.1 설계 방향: 결과물에서 거꾸로

과제별 하네스는 다음 순서로 설계하고, 수정도 같은 순서로 따라간다.

```
원하는 결과물(output_schema) → 필요한 정보(policy 필드·가중치) → 질문 흐름(policy flow·prompts) → 검증 기준(validators)
```

공통 `base.py`에는 모든 과제에서 정말 똑같은 것만 둔다: 세션 상태 조작, 단계 실행 순서, Provider 호출, trace 기록. 과제마다 달라질 수 있는 것은 전부 과제 폴더에 둔다.

### 4.2 공통 파이프라인 (`BaseHarness`)

설계서 4장의 흐름을 단계 하나 = 메서드 하나로 나눈다. 과제 하네스는 필요한 메서드만 오버라이드한다.

| 단계 | 메서드 | 담당 | 준비 단계 구현 |
|---|---|---|---|
| 입력 진단 | `diagnose(state, raw_input)` | LLM | Provider 호출 틀. Mock은 원문을 첫 필드의 사실로 넣는다 |
| 다음 질문 선택 | `select_question(state)` | 코드 + LLM | 고정 우선순위·가중치로 미충족 필드 중 첫 번째를 고르는 로직 **실제 구현**. 모르겠어요 중인 필드가 있으면 그 필드가 우선. 문구·선택지는 policy의 기본값 사용, LLM 생성은 자리만 |
| 쉬운 질문 만들기 | `make_easier_question(state, field, level)` | policy 사다리 → LLM | 사다리 단계 진행 로직 **실제 구현**, LLM 생성은 Provider 틀 (4.4) |
| 답변 반영 | `apply_answer(state, answer)` | 코드 | **실제 구현**. 아래 4.4 참고 |
| 준비도 | `readiness(state)` | 코드 | **실제 구현**. 아래 4.5 참고 |
| 종료 판단 | `should_stop(state)` | 코드 | **실제 구현** |
| 프롬프트 조립 | `_call()` 내부 | 코드 + 템플릿 | `prompts/{stage}.md`를 Jinja2로 렌더링 (과제 폴더 우선, 없으면 공통) |
| 생성 | `generate(state)` | LLM | Provider 호출 후 `output_schema`로 파싱 |
| 출력 검증 | `validate(state, result)` | 코드 + LLM | 스키마 검증 + 공통·과제 `validators.py` 규칙 실행. LLM 검토는 `llm_validation: true`일 때만 |

**trace:** 모든 단계 호출은 `state.trace`에 `{stage, input, output, provider, usage, at}`로 남는다. 하네스 튜닝 때 "왜 이 질문이 나왔나", "어느 단계에서 틀어졌나"를 보는 기본 도구다. Provider의 토큰 사용량도 여기 쌓여 비용 추적에 쓴다.

**하네스 프로필:** 설계서 6.4의 설정값(`coaching_style`, `assumption_policy`, `alternative_count` 등)은 `HarnessProfile` 모델로 정의하고 파이프라인에 인자로 전달한다. 준비 단계에서는 기본값만 쓰고, 온보딩 설문으로 채우는 것은 범위 밖이다.

### 4.3 과제 폴더 구성

```
tasks/<task_type>/
├── output_schema.py   # ① 결과물 Pydantic 모델 (기준점)
├── policy.yaml        # ② 필드·가중치·질문 유형·흐름·모드별 상한·준비도 기준·금지 규칙
├── prompts/           # ③ 단계별 프롬프트 템플릿 (Jinja2 .md) — 이 과제에서 바꾸는 것만 둔다
├── validators.py      # ④ 과제 전용 검증 규칙 함수 목록
├── harness.py         # BaseHarness 서브클래스. 처음엔 비어 있음
└── evals/             # 샘플 입력 시나리오(YAML). 하네스 수정 후 회귀 확인용
```

프롬프트 단계는 `diagnose`, `easier_question`, `propose_value`, `generate`, `validate` 다섯 개다. 공통 기본 템플릿은 `harness/prompts/`에 있고, 과제 폴더 `prompts/`에 같은 이름의 파일이 있으면 그것이 우선한다. 준비 단계에서는 과제마다 `generate.md`만 덮어쓴다(공통 `_generate_base.md`를 상속해 과제 지침 블록만 채움). 과제별 튜닝이 진행되면 필요한 단계 파일을 과제 폴더에 추가하면 된다.

`policy.yaml`의 `raw_input_field`는 사용자의 첫 한 줄 입력을 어느 필드의 사실로 둘지 정한다(예: 상품기획은 `product_idea`). `llm_validation`(기본 false)은 생성 후 LLM 검토 호출 여부로, 비용 때문에 기본으로 끈다.

`evals/`의 시나리오는 `app/harness/evals.py`의 `run_scenario()`로 돌린다. 테스트는 Mock으로 돌리고, 나중에 실제 모델이 붙으면 같은 시나리오로 품질을 비교하는 데 쓴다.

`policy.yaml` 형태:

```yaml
task_type: product_planning
title: 상품기획
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
fields:
  - name: product_idea
    label: 상품 아이디어
    kind: must_confirm        # must_confirm | ai_suggest | default
    weight: 3
    question: 어떤 상품을 만들고 싶으신가요?
    easier_questions:         # "모르겠어요" 사다리. 아래로 갈수록 쉬워진다 (4.4 참고)
      - question: 지금 만들고 있거나 만들 수 있는 물건을 하나만 말해 주세요.
      - question: 아래 중 가장 가까운 걸 골라 주세요.
        options: [향초·디퓨저, 액세서리, 문구·굿즈, 의류·패브릭]
    options: []               # 비어 있으면 직접 입력만
    multi_select: false
  # ...
rules:                        # 금지·주의 규칙 (생성 프롬프트와 validators에 전달)
  - 고객 문제와 무관한 기능 확대를 제안하지 않는다
```

필드의 순서가 곧 고정 우선순위다(설계서 13장 MVP: 고정 우선순위). 정보 이득 기반 순서는 2차.

### 4.4 답변 처리

| 답변 방식 | 처리 |
|---|---|
| `option` (선택지 채택) | 사실로 저장, source=`user_selected_ai_option`, confidence 1.0 |
| `free_text` (직접 입력) | 사실로 저장, source=`user_free_text`, confidence 1.0 (LLM 필드 추출은 이후) |
| `dont_know` (모르겠어요) | **다음 필드로 넘어가지 않는다.** 같은 필드를 한 단계 더 쉬운 질문으로 다시 묻고, 답을 얻을 때까지 반복한다 (아래 "쉬운 질문 사다리") |
| `skip` (건너뛰기) | 사용자가 명시적으로 넘긴 경우에만. unknowns에 남기고 다음 필드로 |

**쉬운 질문 사다리.** "모르겠어요"는 그 필드를 포기하는 신호가 아니라 질문이 어렵다는 신호로 본다. 필드마다 `dont_know_level`을 두고, 모르겠어요가 올 때마다 1씩 올리며 그 단계의 질문을 낸다.

1. **policy 사다리**: `easier_questions`에 적힌 순서대로. 아래로 갈수록 추상 질문 → 구체 예시 → 비교 선택 순으로 쉬워지게 쓴다.
2. **LLM 쉬운 질문 생성**: policy 사다리를 다 쓰면 `make_easier_question(state, field, level)` 단계가 지금까지의 답변 맥락과 앞서 실패한 질문들을 받아, 그보다 쉬운 질문과 선택지를 만든다. 준비 단계에서는 Provider 호출 틀만 두고 Mock은 결정적인 선택형 질문을 돌려준다.
3. **바닥 단계 — AI 제안 확인**: 일정 단계(`policy.max_easier_level`, 기본 4) 이상이면 질문 형태를 "AI가 맥락으로 추정한 후보를 보여주고 고르거나 고치게" 바꾼다. 예/아니오나 하나 고르기 수준이라 어떤 사용자도 답할 수 있다. 여기서 채택한 값은 source=`user_selected_ai_option`의 사실이 된다. 여기서도 모르겠어요면 다른 후보로 다시 제안한다.

이 흐름에서 빠져나가는 방법은 답하기, 건너뛰기, "이대로 결과 만들기" 세 가지뿐이며, 셋 다 사용자의 명시적 선택이다. 쉬운 질문으로 다시 묻는 것은 질문 상한(4.5)에 세지 않는다. 상한은 "몇 개의 필드를 물었는가"를 센다. 각 시도는 `asked_questions`에 `level`과 함께 남아 trace에서 사다리가 어떻게 내려갔는지 볼 수 있다.

수정(`PATCH`)은 해당 필드 값을 바꾸고, 같은 세션에 결과가 있으면 그 결과를 "재생성 필요"로 표시한다. 영향 필드 계산(CX-02)은 이후.

### 4.5 준비도와 종료

- `readiness = Σ(채워진 필드 가중치 × 계수) / Σ(전체 필드 가중치)`. 계수: 사실 1.0, AI 가정 0.5, 미확인 0.
- 종료 조건(하나라도 참이면 질문 중단, "최종 확인" 상태로):
  1. `must_confirm` 필드가 모두 사실로 채워지고 `readiness ≥ readiness_threshold`
  2. 질문 수가 모드 상한에 도달 (빠른 3 / 기본 5 / 정밀 10). 설계서 5.5는 기본 5~7이지만 MVP(13장)는 최대 5문항이므로 기본값을 5로 두고 policy에서 조정한다
  3. 묻지 않은 필드가 남아 있지 않음
- 사용자는 어느 상태에서든 `generate`를 부를 수 있다(설계서 원칙 8).

### 4.6 과제별 초안 내용

`policy.yaml`의 필드 순서는 설계서 7장 권장 흐름, `rules`는 7장 금지·주의, `output_schema`는 설계서 3장 대표 산출물과 기능 설계 클래스 다이어그램을 따른다.

| 과제 | 필드(순서) | 결과물 주요 항목 |
|---|---|---|
| `business_plan` | 사업 아이디어 → 고객 문제 → 목표 고객 → 현재 대안 → 해결 방식 → 수익모델 → 보유 자원 → 검증 방법 | 고객 문제, 해결책, 수익모델, 위험, 검증 계획 |
| `product_planning` | 상품 아이디어 → 사용자 → 사용 상황 → 고객 문제 → 핵심 가치 → MVP → 제작 제약 → 가격 방향 | 가치제안, 핵심 기능, MVP, 가격 방향, 검증 실험 |
| `branding` | 상품과 고객 → 고객이 느낄 가치 → 차별점 → 원하는 인상 → 피할 인상 → 브랜드 성격 → 톤앤매너 → 네이밍·슬로건 | 포지셔닝, 브랜드 키워드, 톤앤매너, 네이밍·슬로건 방향 |
| `marketing_content` | 홍보 상품 → 목표 고객 → 콘텐츠 목적 → 채널 → 핵심 메시지 → 근거 → 행동 유도 → 톤·길이 | 채널, 핵심 메시지, 콘텐츠 본문(SNS·광고·상세·숏폼 중 선택 채널), CTA |

모든 과제의 결과물은 공통 래퍼를 가진다: `cards`(유형 진단·제안·실행, 제목, 본문, 순서), `assumptions`(AI가 보완한 항목과 확인 필요 여부), `full_text`(완성본). 과제별 항목은 래퍼 안의 `content`에 들어간다.

## 5. 세션 상태 (`core/state.py`)

설계서 10.2·12장 구조를 그대로 옮긴다.

```
SessionState
  session_id, task_type, mode(quick|standard|precise), status, profile: HarnessProfile
  raw_input
  facts:       {field: InfoItem}      # InfoItem = value, source, confidence, updated_at
  assumptions: {field: Assumption}    # + reason, requires_confirmation
  unknowns:    [field]
  dont_know_levels: {field: int}      # 모르겠어요 사다리 현재 단계
  conflicts:   [Conflict]             # 준비 단계에선 비어 있음
  asked_questions: [AskedQuestion]    # question_id, field, level, answer_type, value, at
  readiness: float
  result: GenerationResult | None, result_stale: bool
  validation: ValidationReport | None
  trace: [TraceEntry]
```

- `status`: `drafting → clarifying → confirming → generating → completed`, 실패 시 `failed`, 수정 시 `revising` (기능 설계 SessionStatus).
- `source`: `user_free_text | user_selected_ai_option | previous_task | ai_assumption | default`.

## 6. API 계약

기본 경로 `/api/v1/coaching`.

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/tasks` | 과제 목록(유형·이름·설명) |
| GET | `/tasks/{task_type}/form` | 입력 예시, 모드 목록, 필드 라벨 |
| POST | `/tasks/{task_type}/sessions` | `{raw_input, mode}` → 세션 생성 + 첫 질문 |
| GET | `/sessions/{id}` | 세션 이어하기(SE-05) |
| POST | `/sessions/{id}/answers` | `{question_id, answer_type, value?, option_ids?}` → 다음 질문 |
| PATCH | `/sessions/{id}/answers/{question_id}` | 이전 답변 수정(IV-08) |
| POST | `/sessions/{id}/generate` | 결과 생성 (준비 단계는 동기 처리) |
| GET | `/sessions/{id}/result` | 결과 조회 |
| GET | `/sessions/{id}/trace` | 하네스 디버깅용 trace. `DEBUG=true`일 때만 노출 |

세션 응답(`SessionView`)은 프론트가 바로 그리는 값을 담는다: `status`, `next_question`(문구·선택지·복수선택·질문 유형·쉬운 질문 여부), `progress`(답한 수/상한, readiness), `summary`(확인된 정보 목록과 출처), `can_generate`. 내부 상태 전체(`trace` 포함)는 응답에 싣지 않는다. 시스템 프롬프트와 정책은 프론트로 내보내지 않는다(설계서 10.3).

## 7. Provider

```python
class LLMProvider(Protocol):
    name: str
    def complete(self, *, task_type: str, stage: str, prompt: str,
                 response_model: type[BaseModel] | None) -> ProviderResponse: ...
# ProviderResponse: text, parsed(BaseModel | None), usage(input_tokens, output_tokens), model
```

- `MockProvider`: 비용 0, 결정적. `response_model`이 있으면 JSON Schema를 따라 `"[mock] <필드 설명>"` 형태의 값으로 자동으로 채운 인스턴스를 돌려준다. 그래서 `output_schema`를 고쳐도 Mock을 따로 고칠 필요가 없다.
- `ClaudeProvider`는 이번 범위 밖. `.env`의 `PROVIDER` 값으로 고르는 자리만 `config.py`/`registry`에 둔다.

## 8. 오류 처리

- Provider 호출 실패 → 세션 `status=failed`, 입력과 답변은 그대로 유지, 같은 `generate`로 재시도(GE-09). 응답은 오류 코드와 사용자 안내 문구.
- 생성 결과가 `output_schema` 파싱에 실패 → 1회 재요청 후에도 실패하면 위와 같이 `failed`.
- 없는 세션 404, 잘못된 `task_type` 404, 잘못된 `question_id`·`answer_type` 422.

## 9. 프론트엔드 (준비 단계)

- Vite + React + TS 프로젝트, 개발 서버는 `/api`를 `localhost:8000`으로 프록시.
- `npm run gen:api`: 실행 중인 백엔드의 `/openapi.json`에서 `src/api/schema.d.ts` 생성.
- 디자인 없는 최소 화면 하나: 과제 선택 → 한 줄 입력 → 질문 카드(선택지/직접 입력/모르겠어요/건너뛰기) → "이대로 결과 만들기" → 결과 카드. 실제 화면은 디자인 HTML을 받으면 교체한다. 이 화면의 목적은 계약과 흐름이 끝까지 이어지는지 확인하는 것이다.

## 10. 테스트

모두 MockProvider로 돌고 키·비용이 필요 없다.

- `test_base_harness.py`: 답변 방식별 반영·출처, 준비도 계산, 모드별 종료, 모르겠어요 연속 시 같은 필드에 머물며 사다리를 끝까지 내려가 AI 제안 확인 단계에 도달하는지, 재질문이 상한에 세지 않는지.
- `test_task_policies.py`: 과제 4개를 파라미터로 돌며 `policy.yaml` 로딩, 필드 이름 중복 없음, 프롬프트 파일 존재, Mock 생성 결과가 `output_schema`를 통과하는지 확인. 과제 폴더를 고쳤을 때 깨진 곳을 잡는 안전망.
- `test_api_flow.py`: 세션 생성 → 답변 → 수정 → 생성 → 결과 조회 전체 흐름.

## 11. 완료 기준

1. `backend/`에서 `uv run pytest` 통과.
2. `uv run fastapi dev app/main.py` 후 `/docs`에서 세션 생성부터 Mock 결과 조회까지 한 사이클이 된다.
3. `frontend/`에서 `npm run gen:api`, `npm run build`, `npm run dev`가 되고 최소 화면으로 같은 사이클이 된다.
4. `CLAUDE.md`에 구조, 실행 명령, 과제 하네스 수정 절차(4.1 순서), 디자인 HTML 수령 절차가 있다.

## 12. 범위 밖

실제 LLM(Claude) 연결, DB, 로그인·사용자, 온보딩 설문(ON), 과제 간 컨텍스트 연결(CX), 개인화·기억(PM), 운영 관리(AD), 스토어 확장(SA·CG·NA·AU), LLM 기반 모호성·충돌 탐지, 정보 이득 기반 질문 순서, 결과 내보내기.
