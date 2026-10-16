# AX 코칭 플랫폼

창작자가 좋은 프롬프트를 쓰지 못해도 과제별 적응형 질문으로 생각을 구체화해 사업계획·상품기획·브랜딩·마케팅 콘텐츠 결과물로 바꾸도록 돕는 모바일 친화형 코칭 플랫폼. 학교 수업 팀 프로젝트다(개발 1명, 디자인 1명).

- 기획 근거: `docs/planning/` (기능 설계, 기획 및 하네스 설계서 — PDF와 추출 텍스트)
- 현재 설계·계획: `docs/superpowers/specs/`, `docs/superpowers/plans/`
- **요구사항·디자인·하네스는 자주 바뀐다.** 바뀌었을 때 고칠 곳이 적은 쪽을 고른다.

## 실행

| 할 일 | 명령 (저장소 루트에서) |
|---|---|
| 백엔드 테스트 | `uv run --directory backend pytest` |
| 백엔드 서버 | `uv run --directory backend fastapi dev app/main.py` → http://localhost:8000/docs |
| 프론트 테스트 | `npm --prefix frontend test` (vitest) |
| 프론트 타입 재생성 | `npm --prefix frontend run gen:api` |
| 프론트 개발 서버 | `npm --prefix frontend run dev` → http://localhost:5173 (`/api`는 8000으로 프록시) |
| 프론트 빌드·타입 검사 | `npm --prefix frontend run build` |

Windows에서 응용 프로그램 제어 정책이 `uvicorn.exe` 직접 실행을 막으면 `uv run --directory backend python -m uvicorn app.main:app --port 8000`을 쓴다.

## 구조

- `backend/app/harness/base.py` — 모든 과제가 공유하는 파이프라인. 단계 하나 = 메서드 하나.
- `backend/app/harness/tasks/<task>/` — 과제별 하네스 전부(결과물 스키마, 정책, 프롬프트, 검증, 시나리오).
- `backend/app/harness/prompts/` — 공통 프롬프트. 과제 폴더 `prompts/`에 같은 이름이 있으면 그게 우선.
- `backend/app/harness/registry.py` — 과제 등록부(`TASK_TYPES`). 등록되지 않은 과제는 `build_harness`가 거부한다.
- `backend/app/api/` — 얇은 라우터(`/api/v1/coaching/...`).
- `backend/app/core/` — 세션 상태(`state.py`), 결과(`results.py`), 저장소(`store.py`), 응답 모델의 공통 부모 `ContractModel`(`contract.py`).
- `backend/app/providers/` — 모델 제공자. 지금은 `MockProvider`만 있다.
- `backend/app/schemas/` — API 요청·응답 스키마.
- `frontend/src/api/coaching.ts` — 백엔드 호출은 전부 여기를 거친다. `schema.d.ts`는 생성물이므로 손으로 고치지 않는다.
- `frontend/src/lib/` — 화면 로직(순수 함수). `components/`는 표시만 한다.
- `design/` — 디자인 HTML 원본. 고치지 않는다.

## 과제 하네스를 고칠 때

결과물에서 거꾸로 따라간다.

1. `output_schema.py` — 원하는 결과물이 바뀌었나?
2. `policy.yaml` — 그 결과물에 필요한 정보(필드·가중치·종류), 질문 문구와 순서, '모르겠어요' 사다리(`easier_questions`), 모드별 질문 상한(`question_caps`), 준비도 기준(`readiness_threshold`), 금지 규칙(`rules`)
3. `prompts/` — 이 과제에서만 다르게 할 단계 템플릿 (`diagnose`, `easier_question`, `propose_value`, `generate`, `validate`)
4. `validators.py` — 결과를 기계적으로 확인할 규칙
5. `harness.py` — 위로 표현할 수 없는 로직만 `BaseHarness` 메서드를 오버라이드
6. `evals/*.yaml` — 바뀐 흐름을 시나리오로 남긴다

고친 뒤 `uv run --directory backend pytest`. `tests/test_tasks.py`가 정책·템플릿·시나리오·스키마가 서로 맞는지 확인한다. 하네스 동작을 볼 때는 `GET /api/v1/coaching/sessions/{id}/trace`(`DEBUG=true`일 때만 열림)로 단계별 프롬프트와 응답을 본다. 검증 요약은 `kind: "summary"` 항목으로 남는다.

새 과제를 추가할 때는 폴더를 만들고 `app/harness/registry.py`의 `TASK_TYPES`에 넣는다.

## 하네스 원칙 (설계서 2.2, 16장)

- 부족한 정보는 질문하고, 모호한 정보는 확인한다. 선택지는 제안일 뿐이며 직접 입력을 항상 허용한다.
- '모르겠어요'는 포기가 아니라 질문이 어렵다는 신호다. 같은 필드를 더 쉽게 물어 답을 얻을 때까지 머문다(policy 사다리 → LLM 쉬운 질문 → AI 후보 제안). 빠져나가는 길은 답하기·건너뛰기·결과 만들기뿐이다.
- AI가 보완한 정보는 가정(`assumptions`)으로 두고 사실(`facts`)과 섞지 않는다. 모든 정보에 출처를 남긴다.
- 사용자는 언제든 현재 정보로 결과를 만들 수 있다.
- 답변 처리는 원자적이다. 도중에 실패하면 세션 상태가 바뀌지 않는다.
- 시스템 프롬프트와 정책은 프론트로 내보내지 않는다.
- 오류 본문은 `{"detail": "<한국어 문장>"}`이다. 제공자 오류 문구는 노출하지 않는다. `generate`가 실패하면 일반 안내 문구만 응답하고 상세는 trace에 남긴다.

## API 계약이 바뀔 때

1. `backend/app/schemas/`(또는 응답에 실리는 `app/core/state.py`·`results.py`의 모델)를 고친다. 응답에 실리는 새 모델은 `ContractModel`을 상속해야 생성된 프론트 타입에서 필드가 선택(`?:`)으로 느슨해지지 않는다.
2. `uv run --directory backend pytest`
3. `npm --prefix frontend run gen:api` → `npm --prefix frontend run build`에서 나는 타입 오류를 따라 프론트를 고친다.

## 디자인 HTML을 받았을 때

`design/README.md`의 절차를 따른다. 원본은 날짜 폴더에 그대로 두고, 직전 버전과 diff해 바뀐 화면만 React에 반영한다. 디자인 때문에 API가 바뀌어야 하면 위 "API 계약이 바뀔 때"를 먼저 한다.

## 코드 품질 기준

- 함수와 모듈은 기능적 응집도를 목표로 한다. 하나가 한 가지 일만 한다.
- 모듈끼리는 데이터 결합으로 통신한다. 필요한 데이터만 넘긴다.
- 피한다: 제어 결합(동작을 바꾸는 플래그 인자), 공통 결합(전역·변경 가능한 모듈 상태), 스탬프 결합(필드 하나면 되는데 큰 구조체를 통째로 넘기기).
- 판단은 값을 받아 값을 돌려주는 순수 함수로 만든다. 상태 변경은 한 곳에서만 한다.
- 과제 계약이라 그대로 둔다: `stage(self, state)` 형태의 오버라이드 구조, `Validator(state, result, policy)` 시그니처.
- 백엔드 라우터는 얇게 둔다. 프론트 컴포넌트는 URL 경로를 직접 들지 않고 `src/api/coaching.ts`를 거친다.

## 개발 방식

- 항상 TDD: 실패하는 테스트 → 구현 → 통과.
- 작업마다 `task/<번호>-<이름>` 브랜치를 따고 PR을 올려 squash merge한다.
- 커밋 메시지와 PR 본문에 AI 공동저자·생성 표기를 넣지 않는다(저자는 사용자 단독).

## 비용

학교 수업이라 LLM 비용을 아낀다. 개발·테스트는 `MockProvider`(`PROVIDER=mock`, 기본값)로 한다. 실제 모델 어댑터를 추가할 때는 `app/providers/`에 `LLMProvider`를 구현하고 `factory.py`에 등록한다. 테스트는 계속 Mock으로 돌아야 한다. `policy.llm_validation`은 생성마다 호출이 하나 늘어나므로 기본으로 끈다.
