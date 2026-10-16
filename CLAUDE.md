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
| 하네스 튜닝(YAML·프롬프트 저장 시 재시작) | `uv run --directory backend python -m uvicorn app.main:app --reload --reload-include "*.yaml" --reload-include "*.md"` |
| 프론트 테스트 | `npm --prefix frontend test` (vitest) |
| 프론트 타입 재생성 | `npm --prefix frontend run gen:api` |
| 프론트 개발 서버 | `npm --prefix frontend run dev` → http://localhost:5173 (`/api`는 8000으로 프록시) |
| 프론트 빌드·타입 검사 | `npm --prefix frontend run build` |
| 화면 미리보기 갤러리 | `npm --prefix frontend run dev` → http://localhost:5173/preview (백엔드 없이 모든 화면 상태) |

Windows에서 응용 프로그램 제어 정책이 `uvicorn.exe` 직접 실행을 막으면 `uv run --directory backend python -m uvicorn app.main:app --port 8000`을 쓴다.

설정은 `backend/.env`(실행 위치와 상관없이 이 파일)나 환경 변수에서 읽는다. `DEBUG` 기본값은 `false`이고, `.env.example`을 복사하면 로컬 개발용으로 `DEBUG=true`가 된다.

배포: 세션별 잠금(`app/api/locks.py`)과 메모리 저장소(`InMemorySessionStore`)는 서버 프로세스 하나를 전제로 한다. 인스턴스(워커)는 하나만 띄우고, 공유 저장소가 생기면 둘 다 그쪽으로 바꾼다.

줄바꿈은 `.gitattributes`가 LF로 고정한다(`design/**`는 받은 바이트 그대로, PDF·이미지는 바이너리).

## 구조

- `backend/app/harness/base.py` — 모든 과제가 공유하는 파이프라인. 단계 하나 = 메서드 하나.
- `backend/app/harness/tasks/<task>/` — 과제별 하네스 전부(결과물 스키마, 정책, 프롬프트, 검증, 시나리오).
- `backend/app/harness/prompts/` — 공통 프롬프트. 과제 폴더 `prompts/`에 같은 이름이 있으면 그게 우선. 단계 템플릿은 `{% block system %}`(과제 설명 `_task.md`·규칙·지침·할 일 — 과제마다 고정이라 캐시되는 앞부분)과 `{% block user %}`(세션 맥락 `_context.md`·이번 요청)로 나뉜다. 출력 구조(JSON Schema)는 제공자가 `response_model`로 강제하므로 프롬프트에 싣지 않는다.
- `backend/app/harness/prompting.py` — 단계별 템플릿 변수 선언(`STAGE_CONTEXT`). 넘긴 키가 선언과 다르면 렌더링이 실패한다. 렌더 결과는 `Prompt(system, user)`.
- `backend/app/harness/registry.py` — 과제 등록부(`TASK_TYPES`). 등록되지 않은 과제는 `build_harness`가 거부한다.
- `backend/app/api/` — 얇은 라우터(`/api/v1/coaching/...`), 상태→응답 변환(`views.py`, 순수 함수), 예외 처리기(`errors.py`), 경로별 오류 응답 선언(`responses.py`), 세션별 잠금(`locks.py`).
- `backend/app/core/` — 세션 상태(`state.py`, 출처 라벨 `SOURCE_LABELS` 포함), 결과(`results.py`), 저장소(`store.py`, 계약은 `tests/test_store_contract.py`), 응답 모델의 공통 부모 `ContractModel`(`contract.py`), 사용자에게 보이는 실패 문구(`messages.py`).
- `backend/app/providers/` — 모델 제공자. 지금은 `MockProvider`만 있다. `mock_fill.py`가 스키마 제약(길이·개수·범위·형식)을 지키는 Mock 값을 만든다.
- `backend/app/schemas/` — API 요청·응답 스키마.
- `frontend/src/api/coaching.ts` — 백엔드 호출은 전부 여기를 거친다. `schema.d.ts`는 생성물이므로 손으로 고치지 않는다.
- `frontend/src/lib/` — 화면 로직(순수 함수). `screen.ts`의 `screenOf`가 지금 화면(초기·정보 부족·생성 중·완료·실패·수정)을, `sessionActions`가 아래쪽 버튼(최신 결과가 있으면 새 생성 없이 `결과 보기`가 먼저)을 정하고 App은 그것으로 그린다. `components/`는 표시만 한다.
- `frontend/src/styles/tokens.css` — 디자인 원시 값(색·글꼴·글자 크기·간격·모서리·폭·선 두께)은 여기에만 둔다. 다른 CSS에서 색과 글자 크기·폭·선·모서리는 `var(--…)`만 쓴다(`tokens.test.ts`가 검사한다. 컴포넌트 안쪽 여백의 잔값과 위치 값은 예외).
- `frontend/src/layout/` — 앱 뼈대(왼쪽 메뉴·헤더·본문·오른쪽 패널). props만 받는다. 배치는 창 폭이 아니라 뼈대 폭(`@container app`)으로 바뀐다(미리보기 390px 프레임도 모바일 배치).
- `frontend/src/preview/` — 미리보기 갤러리. 앱과 같은 컴포넌트를 샘플 데이터(`fixtures.ts`, 생성된 API 타입)로 그린다. 새 화면 상태를 만들면 `frames.tsx`에 프레임을 더한다. 프레임 폭은 `--preview-desktop`·`--preview-mobile` 토큰이고, 프레임을 감싸는 스크롤 상자를 두지 않는다(html.to.design이 잘린 채 가져온다).
- `design/` — 디자인 HTML 원본. 고치지 않는다.

## 과제 하네스를 고칠 때

결과물에서 거꾸로 따라간다.

1. `output_schema.py` — 원하는 결과물이 바뀌었나?
2. `policy.yaml` — 그 결과물에 필요한 정보(필드·가중치·종류), 질문 문구와 순서, '다른 예시 보기' 사다리(`easier_questions`, `max_easier_level`보다 적게. 고정 단계는 기본 단일 선택이고 `multi_select: true`로 바꾼다), 모드별 질문 상한(`question_caps`, 양의 정수), 준비도 기준(`readiness_threshold`), 금지 규칙(`rules`)
3. `prompts/` — 이 과제에서만 다르게 할 단계 템플릿 (`diagnose`, `easier_question`, `propose_value`, `generate`, `validate`). 과제마다 고정인 내용은 `system` 블록, 세션 값은 `user` 블록에 둔다(`generate`는 보통 `task_guidance` 블록만 덮는다). 단계마다 쓸 수 있는 변수는 `prompting.py`의 `STAGE_CONTEXT`에 있다.
4. `validators.py` — 결과를 기계적으로 확인할 규칙. '이 표현이 있으면 경고'는 `validation.term_rule(rule, terms, message_template)`로 만든다.
5. `harness.py` — 위로 표현할 수 없는 로직만 `BaseHarness` 메서드를 오버라이드
6. `evals/*.yaml` — 바뀐 흐름을 시나리오로 남긴다

고친 뒤 `uv run --directory backend pytest`. `tests/test_tasks.py`가 정책·템플릿·시나리오·스키마가 서로 맞는지 확인한다.

- 정책·시나리오 YAML은 모르는 키를 거부한다. 오타는 조용히 무시되지 않고 읽을 때 실패한다.
- 단계마다 선언된 변수만 넘겨 모든 템플릿을 렌더링한다. 다른 단계 변수를 쓰면 실패한다. system·user가 모두 비어 있지 않고, system에 세션 값(처음 입력)이 섞이지 않고, 빈 줄이 두 개 연속 나오지 않아야 한다.
- 시나리오는 끝까지 돌아 `expect_status`에 닿아야 하고 결과는 과제 스키마를 통과해야 한다. `answers`의 키는 물을 수 있는(kind가 default가 아닌) 필드여야 하고, 계획한 답은 모두 쓰여야 한다. 흐름이 바뀌어 답이 남으면 시나리오 이름과 함께 실패한다. 생성 실패는 예외가 아니라 `failed` 상태로 끝나므로 `expect_status: failed` 시나리오도 쓸 수 있다.
- `tasks/` 아래 `harness.py`가 있는 폴더와 `TASK_TYPES`가 같아야 한다.

하네스 동작을 볼 때는 `GET /api/v1/coaching/sessions/{id}/trace`(`DEBUG=true`일 때만 열림)로 단계별 프롬프트(`input.system`·`input.user`)와 응답, 제공자(`provider`)와 실제 모델 id(`model`, 실패한 호출은 null)를 본다. 검증 요약은 `kind: "summary"` 항목으로 남는다.

새 과제를 추가할 때는 폴더를 만들고 `app/harness/registry.py`의 `TASK_TYPES`에 넣는다.

## 하네스 원칙 (설계서 2.2, 16장)

- 부족한 정보는 질문하고, 모호한 정보는 확인한다. 선택지는 제안일 뿐이며 직접 입력을 항상 허용한다.
- 질문 화면의 '아직 모르겠어요'(`skip`)는 그 필드를 미정(`unknowns`)으로 두고 다음 질문으로 넘어간다. 질문이 어려우면 '다른 예시 보기'(`easier`)로 같은 필드를 한 단계 더 쉽게 묻는다(policy 사다리 → LLM 쉬운 질문 → AI 후보 제안). 사다리에 있는 동안은 그 필드에 머물고, '원래 예시 보기'(`POST /sessions/{id}/question/original`, LLM 호출 없음)는 사다리를 지우고 기본 질문으로 돌아간다. 질문 상한은 기본 질문(level 0)에 답한 필드 수로 센다(같은 필드는 한 번).
- AI가 보완한 정보는 가정(`assumptions`)으로 두고 사실(`facts`)과 섞지 않는다. 모든 정보에 출처를 남긴다. 세션의 가정은 LLM이 다시 적어 주길 믿지 않고 `generate`가 코드로 결과 가정에 합친다.
- 필드는 내부 이름(`name`)으로 다룬다. 프롬프트는 `이름 (라벨)`로 보여 주고, 화면용 라벨은 API 뷰가 붙인다.
- 사용자는 언제든 현재 정보로 결과를 만들 수 있다. 일찍 만들어도 질문은 끝나지 않는다: `POST /sessions/{id}/continue`(`BaseHarness.resume`)가 평소 규칙으로 다음 질문을 걸고, 남은 질문이 없으면 세션을 그대로 둔다. 결과는 그대로 남고 새 답이 생기면 stale이 된다.
- 답변 처리는 원자적이다. 도중에 실패하면 세션 상태가 바뀌지 않는다. 같은 세션을 바꾸는 요청(답변·수정·생성·이어 가기)은 세션별 잠금으로 한 번에 하나씩 돈다.
- 값을 정한 답(답변·수정)이 생기면 같은 필드의 이전 기록은 `superseded`로 표시된다(trace·디버깅용 이력, 응답에는 아직 싣지 않는다). 지금 값의 기준은 언제나 `facts`다.
- 다른 필드 질문을 둔 채 이전 답을 고쳤는데 이제 멈출 때가 되면, 걸린 질문이 기본 질문(level 0)일 때만 내리고 질문을 끝낸다. 사다리 질문은 둔다.
- 생성이 실패하면 질문·입력은 그대로 두고 `FAILED`로 표시한다. 이전 결과는 남기고 `result_stale`은 건드리지 않는다(입력이 그대로면 여전히 맞는 결과다). `FAILED`는 다음 답변·수정·성공한 생성까지 이어지고, 이어 가기(`continue`)는 걸 질문이 있을 때만 `FAILED`를 푼다(남은 질문이 없으면 다시 생성해야 하므로 그대로 둔다). 질문 단계의 상태(CLARIFYING·CONFIRMING·REVISING)는 `question_status` 한 곳에서 정해지므로, 질문이 걸린 채 수정하거나 이어 가면 CLARIFYING으로 돌아간다. 생성 중 `HarnessError`(입력·규칙 문제)는 세션을 되돌리고 422로 나간다(이미 성공한 LLM 호출의 trace는 저장된다).
- 시스템 프롬프트와 정책은 프론트로 내보내지 않는다.
- 오류 본문은 언제나 `{"detail": "<한국어 문장>"}`(OpenAPI `ErrorBody`)이다. 404(없는 과제·세션·결과·경로), 405, 422(요청 형식·답변 규칙), 500(예상하지 못한 예외), 502(AI 호출·결과 생성 실패) 모두 그렇다. 문구는 `app/core/messages.py`에 모여 있다. OpenAPI에는 경로마다 실제로 낼 수 있는 오류만 `error_responses(...)`로 적는다(500은 공통).
- 내부 사정은 노출하지 않는다. 제공자 원문 오류와 생성 실패 상세는 trace에, 500 예외는 로그에 한 번만 남는다. 422 검증 상세는 로그에 남고, `DEBUG=true`일 때만 422 본문에 `errors`(개발용 선택 필드)로도 실린다.
- `SessionView.error`는 저장값이 아니라 상태에서 나온다(`FAILED`일 때만 생성 실패 문구). 실패 뒤 답하거나, 이전 답을 고치거나, 질문이 걸린 채 이어 가면 함께 사라진다.
- 흐름 패널의 질문 목록(`SessionView.flow`)은 `app/harness/flow.py`의 `plan_flow`(순수)가 만든다. 물어본 필드(처음 물은 순서, 완료·미정) → 지금 질문 → 예정(정책 순서, `questions_left`만큼)이다. 답한 항목에는 그 답을 정한 질문이 실려 있어 그 `question_id`로 답을 고친다.

## API 계약이 바뀔 때

1. `backend/app/schemas/`(또는 응답에 실리는 `app/core/state.py`·`results.py`의 모델)를 고친다. 응답에서 닿는 모든 스키마는 모든 속성을 required로 내야 한다(생성된 프론트 타입이 `?:`로 느슨해지지 않게). `tests/test_contract.py`가 이를 확인하므로 새 응답 모델은 `ContractModel`을 상속하면 된다. 개발용 선택 필드는 그 테스트의 `DEBUG_ONLY_FIELDS`에 이유와 함께 올린다.
   화면용 값(라벨 등)은 LLM이 채우는 모델(`TaskResult`·`ResultAssumption`)이 아니라 `schemas/`의 뷰 모델에 두고 `api/views.py`에서 붙인다(예: `LabeledResult`, `UnknownItem`).
2. `uv run --directory backend pytest`
3. `npm --prefix frontend run gen:api` → `npm --prefix frontend run build`에서 나는 타입 오류를 따라 프론트를 고친다.

## 디자인 HTML을 받았을 때

`design/README.md`의 절차를 따른다. 원본은 날짜 폴더에 그대로 두고, 직전 버전과 diff해 바뀐 화면만 React에 반영한다. 디자인 때문에 API가 바뀌어야 하면 위 "API 계약이 바뀔 때"를 먼저 한다.

배포: 프론트는 버셀(Root Directory `frontend`, `frontend/vercel.json`)에 올린다. main은 정식 주소, PR마다 미리보기 주소가 생긴다. 디자이너는 `/preview`를 html.to.design으로 가져가 수정한다(`design/README.md`). `/preview`는 `cleanUrls`가 `preview.html`로 연결한다(로컬 Vite 서버도 같다). 백엔드 주소는 `VITE_API_BASE`로 정하고, 지금은 백엔드를 배포하지 않아 앱 화면은 미연결 안내를 띄운다. 다른 출처(렌더)를 가리키려면 백엔드에 CORS(버셀 도메인 허용)가 먼저 필요하다. CORS 없이 가려면 `vercel.json`의 `rewrites`로 `/api/:path*`를 렌더로 넘겨 같은 출처로 쓴다(이때 `VITE_API_BASE`는 비운다). 앱 화면에서 JSON이 아닌 실패 응답(버셀 404·프록시·게이트웨이)과 연결 예외는 `BACKEND_UNREACHABLE` 안내로 보인다(`api/client.ts`의 `toOutcome`).

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

학교 수업이라 LLM 비용을 아낀다. 개발·테스트는 `MockProvider`(`PROVIDER=mock`, 기본값)로 한다. 실제 모델 어댑터를 추가할 때는 `app/providers/`에 `LLMProvider`를 구현하고 `factory.py`에 등록한다. `prompt.system`은 시스템 프롬프트(캐시 앞부분), `prompt.user`는 사용자 메시지로 보내고, 출력 구조는 `response_model`로 강제하며, SDK·파싱 오류는 `ProviderError`/`ProviderOutputError`로 감싼다. 테스트는 계속 Mock으로 돌아야 한다. `policy.llm_validation`은 생성마다 호출이 하나 늘어나므로 기본으로 끈다.
