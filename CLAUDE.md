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

저장소는 `STORE`로 고른다. `memory`(기본, 테스트)는 재시작하면 사라지고, `sqlite`(`.env.example`의 로컬 개발값)는 `DATABASE_PATH`(기본 `backend/data/sessions.db`, git에서 제외) 파일에 남는다. 계약은 `tests/test_store_contract.py`가 두 구현에 함께 돌린다. 테스트는 `tests/conftest.py`가 개발자 `.env`와 상관없이 늘 `memory`로 정한다(실제 DB를 건드리지 않는다). 목록 조회(`list_by_owner`)는 무거운 trace를 빼고 읽는다.

배포: 세션별 잠금(`app/api/locks.py`)은 서버 프로세스 하나를 전제로 한다. SQLite 파일도 한 프로세스가 쓴다. 인스턴스(워커)는 하나만 띄우고, 여러 프로세스가 필요해지면 잠금과 저장소를 공유 저장소(DB 잠금)로 함께 바꾼다.

줄바꿈은 `.gitattributes`가 LF로 고정한다(`design/**`는 받은 바이트 그대로, PDF·이미지는 바이너리).

## 구조

- `backend/app/harness/base.py` — 모든 과제가 공유하는 파이프라인. 단계 하나 = 메서드 하나.
- `backend/app/harness/tasks/<task>/` — 과제별 하네스 전부(결과물 스키마, 정책, 프롬프트, 검증, 시나리오).
- `backend/app/harness/prompts/` — 공통 프롬프트. 과제 폴더 `prompts/`에 같은 이름이 있으면 그게 우선. 단계 템플릿은 `{% block system %}`(과제 설명 `_task.md`·규칙·지침·할 일 — 과제마다 고정이라 캐시되는 앞부분)과 `{% block user %}`(세션 맥락 `_context.md`·이번 요청)로 나뉜다. 출력 구조(JSON Schema)는 제공자가 `response_model`로 강제하므로 프롬프트에 싣지 않는다.
- `backend/app/harness/prompting.py` — 단계별 템플릿 변수 선언(`STAGE_CONTEXT`). 넘긴 키가 선언과 다르면 렌더링이 실패한다. 렌더 결과는 `Prompt(system, user)`.
- `backend/app/harness/evidence.py` — 근거 자료(`EvidenceSource`, 과제 폴더 `evidence.yaml`을 `load_evidence`로 읽음)와 점검 문구를 결과 기록으로 바꾸는 순수 함수 `evidence_record`.
- `backend/app/harness/registry.py` — 과제 등록부(`TASK_TYPES`). 등록되지 않은 과제는 `build_harness`가 거부한다.
- `backend/app/api/` — 얇은 라우터(`/api/v1/coaching/...`), 상태→응답 변환(`views.py`, 순수 함수), 예외 처리기(`errors.py`), 경로별 오류 응답 선언(`responses.py`), 세션별 잠금(`locks.py`), 요청한 사용자(`owner.py`), 결과 이미지 파일 바이트(`assets.py`, 주인에게만. 응답은 `Cache-Control: private, no-store`).
- `backend/app/core/` — 세션 상태(`state.py`, 출처 라벨 `SOURCE_LABELS` 포함), 결과(`results.py`), 저장소(`store.py`: 메모리·SQLite, 계약은 `tests/test_store_contract.py`), 파일 저장소(`assets.py`: 결과 이미지 바이트, 메모리·로컬 폴더 `ASSET_DIR`. 세션 저장소 `STORE`와 짝), 응답 모델의 공통 부모 `ContractModel`(`contract.py`), 사용자에게 보이는 실패 문구(`messages.py`).
- `backend/app/providers/` — 모델 제공자. 지금은 `MockProvider`만 있다. `mock_fill.py`가 스키마 제약(길이·개수·범위·형식)을 지키는 Mock 값을 만든다. 이미지는 별도 제공자 `ImageProvider`(`image.py`, Mock은 SVG 자리표시)다.
- `backend/app/schemas/` — API 요청·응답 스키마.
- `frontend/src/api/coaching.ts` — 백엔드 호출은 전부 여기를 거친다. `schema.d.ts`는 생성물이므로 손으로 고치지 않는다.
- `frontend/src/app/` — 앱 상태와 연결. `state.ts`의 `reducer`(순수)만 상태를 바꾼다. 응답은 지금 기다리는 요청 번호(`inflight.seq`)일 때만 받고, 과제·세션 묶음(`contextOf`)을 떠나면 늦게 온 응답을 버린다. `load.ts`의 `needsLoad`가 화면에 모자란 데이터를, `screenModel.ts`가 그릴 화면을 정하고, `handlers.ts`가 버튼을 이동·요청으로 바꾼다(`requests.ts`가 요청 번호를 붙여 실행). 생성 요청(`Call.generating`)이 기다리는 동안은 세션 화면 대신 생성 중 화면, 생성이 실패하면 `failedRoute`로 실패 화면을 보인다. `view.tsx`의 `AppView`는 앱과 미리보기 갤러리가 같이 쓴다. 내 세션 목록(`sessions`)은 목록 화면(홈·내 작업·결과물)에 새로 들어올 때마다 다시 받는다. 내려받는 문서는 `documentFile.ts`가 화면 모델에서 만들고(`lib/documentHtml.ts`, 이스케이프한 HTML 한 파일), 파일 저장(`lib/download.ts`)은 App이 handlers에 넘긴다. 결과 이미지는 화면 불러오기(요청 번호)와 따로 받는다: `app/assets.ts`의 `assetsToLoad`가 고르고 App이 `loadAsset`(헤더를 붙여 받아 data URL, 실패하면 null)으로 받아 `state.assets`에 둔다. 같은 이미지를 받는 동안은 다시 부르지 않고(`notInFlight`, StrictMode의 effect 두 번 실행 대비) 끝나면 목록에서 뺀다. effect가 할 일은 순수 함수 `assetWork`가 정한다: '받는 중' 요청(`assetRequested`)은 부를 id마다 언제나 하고 내려받기만 `notInFlight`로 거르므로, 받는 중에 세션을 떠났다 돌아와도 늦게 온 응답이 받아들여진다. 버튼을 막지 않고 실패해도 알림 없이 대체 글을 보인다.
- `frontend/src/lib/routes.ts` — 해시 주소. `#/{task}/request`, `#/{task}/mode`(세션 전), `#/s/{id}/question|confirm|result`, `#/s/{id}/failed`(생성 실패), `#/s/{id}/saved/{n}`(저장 완료, 저장한 그 버전), `#/s/{id}/question/{question_id}`(답 고치기), `#/s/{id}/v/{n}`(버전 보기), `#/s/{id}/edit/{order}`(결과 문구 고치기), `#/s/{id}/evidence`(근거 자료 검토), `#/work`(내 작업), `#/documents`(결과물), `#/guide`. 주소를 읽고 만드는 곳은 `parseRoute`·`toHash`뿐이다. 본문 바로가기 같은 문서 안 앵커(`#main`)는 `isRouteHash`가 화면 이동에서 거른다.
- `frontend/src/lib/` — 화면 판단(순수 함수): 흐름 표시(`flowView`), 질문 제목·도움 버튼(`question`), 모드 문구(`modes`), 기준 요약(`criteria`), 결과 문서(`document`), 보완 패널 문구와 대화상자 단계(`supplements`의 `supplementStatus`·`panelAfter`), 결과 버튼(`actions`, 최신 결과가 있으면 새 생성 없이 `결과 보기`가 먼저. 낡은 결과는 저장·내려받기를 막는다: `saveButton.disabled`, 배너 `STALE_BANNER`), 브라우저 저장소(`storage`·`drafts`·`clientId`). `screens/`·`components/`는 props만 받아 그린다. 대화상자 열림처럼 그 부품 안에서 끝나는 UI 상태만 부품이 가진다(`SupplementPanel`: 저장 요청이 성공해야 닫고 연 버튼으로 포커스 복귀, 실패하면 입력을 둔 채 열어 둔다). 근거 버튼·반영 전 버전·안전한 링크(`evidence`, 원문 주소는 http(s)만 링크로), data URL(`dataUrl`).
- `frontend/src/styles/tokens.css` — 디자인 원시 값(색·글꼴·글자 크기·간격·모서리·폭·선 두께)은 여기에만 둔다. 다른 CSS에서 색과 글자 크기·폭·선·모서리는 `var(--…)`만 쓴다(`tokens.test.ts`가 검사한다. 컴포넌트 안쪽 여백의 잔값과 위치 값은 예외).
- `frontend/src/layout/` — 앱 뼈대(왼쪽 메뉴·헤더·본문·오른쪽 패널). props만 받는다. 배치는 창 폭이 아니라 뼈대 폭(`@container app`)으로 바뀐다(미리보기 390px 프레임도 모바일 배치).
- `frontend/src/preview/` — 미리보기 갤러리. 앱과 같은 컴포넌트를 샘플 데이터(`fixtures.ts`, 생성된 API 타입)로 그린다. 새 화면 상태를 만들면 `frames.tsx`에 프레임을 더한다. 프레임 폭은 `--preview-desktop`·`--preview-mobile` 토큰이고, 프레임을 감싸는 스크롤 상자를 두지 않는다(html.to.design이 잘린 채 가져온다). 대화상자를 연 상태는 `dialogFrame`이 같은 양식을 대화상자 표면에 담아 겹쳐 그린다. 이미지는 백엔드 없이 그리므로 픽스처의 data URL(`PREVIEW_IMAGES`)을 쓴다.
- `design/` — 디자인 HTML 원본. 고치지 않는다.

## 과제 하네스를 고칠 때

결과물에서 거꾸로 따라간다.

1. `output_schema.py` — 원하는 결과물이 바뀌었나?
2. `policy.yaml` — 그 결과물에 필요한 정보(필드·가중치·종류), 질문 문구와 순서, '다른 예시 보기' 사다리(`easier_questions`, `max_easier_level`보다 적게. 고정 단계는 기본 단일 선택이고 `multi_select: true`로 바꾼다), 모드별 질문 상한(`question_caps`, 양의 정수), 준비도 기준(`readiness_threshold`), 미확인 정보 항목(`supplement_fields`, 필드와 다른 이름), 금지 규칙(`rules`), 참고 이미지(`image_generation`, 기본 꺼짐·비용), 이어가기 대응(`carry_over`, 대상은 이 정책의 필드)
3. `prompts/` — 이 과제에서만 다르게 할 단계 템플릿 (`diagnose`, `easier_question`, `propose_value`, `generate`, `validate`, `image`). 과제마다 고정인 내용은 `system` 블록, 세션 값은 `user` 블록에 둔다(`generate`는 보통 `task_guidance` 블록만 덮는다). 단계마다 쓸 수 있는 변수는 `prompting.py`의 `STAGE_CONTEXT`에 있다.
4. `evidence.yaml` — 결과를 검토할 근거 자료(지금은 샘플, 없으면 검토 없음). 자료마다 `id`·`title`·`publisher`·`meta`·`summary`·`scope`·`url`(http(s))·`applies_to`(기록을 둘 섹션 종류)·`record`(결과에 붙일 점검 문구 `title`·`text`·`note`·`caution`, 배경 자료면 생략).
5. `validators.py` — 결과를 기계적으로 확인할 규칙. '이 표현이 있으면 경고'는 `validation.term_rule(rule, terms, message_template)`로 만든다.
6. `harness.py` — 위로 표현할 수 없는 로직만 `BaseHarness` 메서드를 오버라이드
7. `evals/*.yaml` — 바뀐 흐름을 시나리오로 남긴다

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
- 생성이 실패하면 질문·입력은 그대로 두고 `FAILED`로 표시한다. 이전 결과는 남기고 `result_stale`은 건드리지 않는다(입력이 그대로면 여전히 맞는 결과다). `FAILED`는 다음 답변·수정·보완 정보 저장(값이 바뀔 때)·성공한 생성까지 이어지고, 이어 가기(`continue`)는 걸 질문이 있을 때만 `FAILED`를 푼다(남은 질문이 없으면 다시 생성해야 하므로 그대로 둔다). '원래 예시 보기'도 질문을 다시 걸므로 `FAILED`를 푼다. 질문 단계의 상태(CLARIFYING·CONFIRMING·REVISING)는 `question_status` 한 곳에서 정해지므로, 질문이 걸린 채 수정하거나 이어 가면 CLARIFYING으로 돌아간다. 생성 중 `HarnessError`(입력·규칙 문제)는 세션을 되돌리고 422로 나간다(이미 성공한 LLM 호출의 trace는 저장된다). 프론트에서는 이 422도 실패 화면으로 가며, 구체 사유는 알림으로 나간다(실패 화면 문구는 고정).
- 시스템 프롬프트와 정책은 프론트로 내보내지 않는다.
- 오류 본문은 언제나 `{"detail": "<한국어 문장>"}`(OpenAPI `ErrorBody`)이다. 404(없는 과제·세션·결과·경로), 405, 422(요청 형식·답변 규칙), 500(예상하지 못한 예외), 502(AI 호출·결과 생성 실패) 모두 그렇다. 문구는 `app/core/messages.py`에 모여 있다. OpenAPI에는 경로마다 실제로 낼 수 있는 오류만 `error_responses(...)`로 적는다(500은 공통).
- 내부 사정은 노출하지 않는다. 제공자 원문 오류와 생성 실패 상세는 trace에, 500 예외는 로그에 한 번만 남는다. 422 검증 상세는 로그에 남고, `DEBUG=true`일 때만 422 본문에 `errors`(개발용 선택 필드)로도 실린다.
- `SessionView.error`는 저장값이 아니라 상태에서 나온다(`FAILED`일 때만 생성 실패 문구). 실패 뒤 답하거나, 이전 답을 고치거나, 보완 정보를 바꿔 저장하거나, 질문이 걸린 채 이어 가거나, '원래 예시 보기'를 누르면 함께 사라진다.
- 흐름 패널의 질문 목록(`SessionView.flow`)은 `app/harness/flow.py`의 `plan_flow`(순수)가 만든다. 물어본 필드(처음 물은 순서, 완료·미정·멈춤) → 지금 질문 → 예정(정책 순서, `questions_left`만큼)이다. 멈춤(`paused`)은 '다른 예시 보기' 중에 결과를 먼저 만들어 걸린 질문이 내려간 필드다. 이미 상한에 셌으므로 예정 자리를 쓰지 않고, 이어 가면 다시 묻는다. 답한 항목에는 그 답을 정한 질문이 실려 있어 그 `question_id`로 답을 고친다.
- 결과는 버전으로 쌓인다(`SessionState.versions`, `ResultVersion`). 생성이 성공할 때마다 `new_version`이 하나를 덧붙이고(첫 번째는 `first`, 그 뒤는 `regenerate`), 마지막 버전의 결과가 지금 결과(`state.result`)다. 버전은 그때의 사실·가정·미정을 복사해 두므로 결과 화면·버전 보기의 '반영한 기준'은 그 버전의 것이다(`ResultView.summary`). 실패한 생성은 버전을 남기지 않는다. `POST /sessions/{id}/versions/{n}/save`가 저장 표시를 하고, `GET …/versions/{n}`이 지난 버전을 보여 준다.
- 근거 자료는 `find_evidence`(지금은 `evidence.yaml`, 웹 검색을 붙이면 이 단계만 바꾼다)가 내고 `GET /sessions/{id}/evidence`가 보여 준다(결과가 있어야 한다). `POST …/evidence/{source_id}/apply`는 그 자료의 점검 문구와 출처를 결과 `evidence`에 붙인 `evidence` 버전이다. 문구 수정처럼 LLM 없이 직전 버전의 기준을 이어받고(`_add_derived_version`) 상태·`result_stale`은 그대로다. 기록은 `applies_to` 종류의 첫 섹션 뒤에 자리 잡고(없으면 문서 끝), 다시 만든 초안으로는 코드가 옮긴다(`carry_evidence`, 생성 프롬프트에는 싣지 않는다). 같은 자료를 다시 반영하면 버전을 만들지 않고, 점검 문구가 없는 배경 자료는 반영할 수 없다(422).
- 다음 과제로 이어가기: `POST /tasks/{task}/sessions`의 `from_session_id`(·`from_version`, 없으면 마지막 버전)로 이전 작업 그 버전의 사실·보완 정보를 새 과제 필드로 가져온다(`harness/carry.py`의 `build_context`, 순수). 필드마다 같은 이름, 그다음 정책 `carry_over`(이전 이름 → 이 과제 필드)에서 그 필드를 가리키는 이름 순서로 고르고 사실이 보완 정보보다 먼저다. 가져온 값은 출처 `previous_task` 사실이라 묻지 않고, 처음 입력 필드는 새 요청 글이 이긴다. 미리보기 `GET /tasks/{task}/context`가 같은 함수를 쓴다. `DELETE /sessions/{id}/context`는 아직 `previous_task`인 값만 지우고 결과가 있으면 최신 여부를 다시 정한다(뺀 필드는 평소 규칙대로 다시 물을 수 있어 AI 호출이 날 수 있다: 404·422·502). 남의·없는 이전 작업은 404. 가져온 결과의 제목·요약은 프롬프트 맥락(`_context.md`)에 실린다.
- 미확인 정보 보완은 정책의 `supplement_fields`(필드와 이름이 겹치지 않는 별도 항목)다. `PUT /sessions/{id}/supplements`가 세션의 `supplements`에 사용자 입력(`user_supplement`, "사용자 입력 · 검증 전")으로 두고, 질문 흐름·준비도에는 넣지 않는다. 값이 바뀌면 수정처럼 `FAILED`를 풀고, 결과가 있으면 `result_stale`을 "답(사실·가정·미정) 또는 보완 정보가 마지막 버전과 다른지"(`answers_changed`·`supplements_changed`)로 다시 정한다(바꿨다 되돌려 마지막 버전과 같아지면 답도 그대로인 한 결과는 다시 최신이고, 답이 바뀐 채면 낡은 채다). 결과가 없으면 `result_stale`은 건드리지 않는다. 보완 정보는 생성과 LLM 검토 프롬프트(user 블록, `_supplements.md`)에만 "보완 정보"로 실린다(질문 단계에는 싣지 않는다). 생성 이유는 `generate_reason`이 정한다: 답(사실·가정·미정)은 그대로이고 보완 정보만 바뀌었으면 `supplement`. 문구 수정(`PATCH /sessions/{id}/result/sections/{order}`)은 LLM 없이 섹션 글을 바꾼 `edit` 버전이고 직전 버전의 기준(사실·가정·미정·보완 정보)을 이어받고 코드 검증도 그 기준으로 돈다. `content`(과제 스키마 값)는 LLM이 쓴 그대로 두고 섹션과 `full_text`(섹션을 이어 붙인 글)만 바꾸므로, `content`를 읽는 과제 검증은 원래 내용을 판정한다. 상태(`FAILED` 포함)와 `result_stale`은 건드리지 않는다. 고친 글이 지금 글과 같으면 버전을 만들지 않는다. 카드 본문(`ResultCard.body`)은 2500자 이하라(LLM 출력 제약. 상한 전에 저장한 옛 카드는 검증 없이 읽는다) 수정 상한(`EditSectionRequest`)을 넘지 않는다. 섹션 `order`는 카드 순서대로 1..n으로 다시 매긴다.
- 결과 이미지는 정책 `image_generation`을 켠 과제(지금은 브랜딩·마케팅)에서만 생성마다 한 장 만든다(`BaseHarness.illustrate`, 단계 `image`). 첫 섹션 끝에 `ImageBlock`(파일 id·대체 글·설명·출처)을 붙이고, 바이트는 `AssetStore`에 세션 주인 것으로 둔다. 이미지는 보조라 제공자가 실패해도 결과는 살리고 경고(`image_unavailable`) 하나로 줄인다. 문구 수정은 글 블록만 바꾸고 이미지 블록은 지킨다. `GET /assets/{asset_id}`가 주인에게만 바이트를 낸다(남의 것·없는 것은 404).
- 세션에는 주인(`owner_id`)이 있다. 지금은 브라우저가 만든 익명 ID를 `X-Client-Id` 헤더로 보내고(`frontend/src/lib/clientId.ts`, `api/client.ts`의 `withClientId`), 백엔드는 `app/api/owner.py`의 `current_owner`로 받는다. 세션 경로는 모두 owner를 받고, 남의 세션은 없는 세션과 같은 404다(잠금도 만들지 않는다). 헤더가 없거나 형식이 틀리면 422. 로그인을 붙일 때는 `current_owner` 하나만 바꾼다. 테스트는 `tests/conftest.py`의 `api_client(app, client_id=...)`를 쓴다. 내 세션 목록은 `GET /sessions`(`SessionSummary`, 최근에 바뀐 순서, 저장한 버전 포함)다.

## API 계약이 바뀔 때

1. `backend/app/schemas/`(또는 응답에 실리는 `app/core/state.py`·`results.py`의 모델)를 고친다. 응답에서 닿는 모든 스키마는 모든 속성을 required로 내야 한다(생성된 프론트 타입이 `?:`로 느슨해지지 않게). `tests/test_contract.py`가 이를 확인하므로 새 응답 모델은 `ContractModel`을 상속하면 된다. 개발용 선택 필드는 그 테스트의 `DEBUG_ONLY_FIELDS`에 이유와 함께 올린다.
   화면용 값(라벨 등)은 LLM이 채우는 모델(`TaskResult`·`ResultAssumption`)이 아니라 `schemas/`의 뷰 모델에 두고 `api/views.py`에서 붙인다(예: `LabeledResult`, `UnknownItem`).
   결과는 섹션·블록이다(`GenerationResult.sections`, `ResultSection`, `TextBlock`). LLM은 카드(`TaskResult.cards`)를 쓰고 `to_generation_result`가 섹션으로 바꾼다. 저장된 옛 결과(`cards`)는 읽을 때 섹션이 된다. 블록은 `TextBlock`·`ImageBlock`(`type`으로 구분)이고, 결과의 근거 기록은 `GenerationResult.evidence`다.
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
- 작업(PR)을 머지할 때마다 WBS(`docs/WBS.xlsx`, 팀 공유용 작업 현황)를 같은 PR에서 고친다: 끝난 작업은 상태 `완료`·완료일·진척률 1·PR 번호, 시작한 작업은 `진행 중`과 시작일, 계획에 없던 작업은 행을 더하고, 기준일(2행)을 오늘로. `uv run --no-project --with openpyxl python scripts/wbs.py list|set|add|date`로 고친다(엑셀에서 직접 고친 다른 칸은 그대로 둔다). 단계 행 진척률과 '요약' 시트는 수식이라 손대지 않는다.

## 비용

학교 수업이라 LLM 비용을 아낀다. 개발·테스트는 `MockProvider`(`PROVIDER=mock`, 기본값)로 한다. 실제 모델 어댑터를 추가할 때는 `app/providers/`에 `LLMProvider`를 구현하고 `factory.py`에 등록한다. `prompt.system`은 시스템 프롬프트(캐시 앞부분), `prompt.user`는 사용자 메시지로 보내고, 출력 구조는 `response_model`로 강제하며, SDK·파싱 오류는 `ProviderError`/`ProviderOutputError`로 감싼다. 테스트는 계속 Mock으로 돌아야 한다. `policy.llm_validation`은 생성마다 호출이 하나 늘어나므로 기본으로 끈다.
