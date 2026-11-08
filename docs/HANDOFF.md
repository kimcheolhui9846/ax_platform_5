# 작업 인수인계 (HANDOFF)

세션이 바뀌어도 이 문서만 읽고 이어서 일할 수 있게 둔다. **PR을 머지할 때마다 같은 PR에서 "지금 상태"와 "다음 할 일"을 고친다**(WBS와 같이).

- 기준일: 2026-11-08
- main: `5f57556` (PR #42까지 머지, 이 PR이 #43)
- 테스트: 백엔드 1136 passed, 프론트 515 passed, 빌드 OK
- 배포(개인 계정, 무료): 앱 https://ax-platform-5.vercel.app · 미리보기 https://ax-platform-5.vercel.app/preview · API https://ax-coaching-api.onrender.com (문서 `/docs`)

새 세션에서는 "docs/HANDOFF.md 읽고 이어서 해"라고 하면 된다. 프로젝트 규칙은 `CLAUDE.md`, 팀 공유용 작업 현황은 `docs/WBS.xlsx`다.

## 지금 상태

디자인 V2 화면 개발(묶음 0~4)과 디자이너 피드백 반영이 끝났다. 실제 Claude 제공자(`ClaudeProvider`)는 준비돼 있지만 이 프로토타입은 `PROVIDER=mock`(비용 0)으로 둔다. 실제 호출·모델 선택·비용은 인수하는 회사가 정한다. 이미지·근거 자료는 아직 Mock·샘플이다.

| 작업 | PR | 내용 |
|---|---|---|
| 백엔드 기반 | #1~#10 | 세션 상태, Mock 제공자, 정책·프롬프트, 질문 흐름, 생성·검증, 과제 4개, API |
| V2 설계 | #11 | `docs/superpowers/specs/2026-10-16-ux-v2-design.md` |
| 묶음 0 | #12 | 디자인 토큰, 앱 뼈대, 미리보기 갤러리(`/preview`), 버셀 설정 |
| 묶음 1 | #13 | 질문 흐름 화면, 답변 종류(skip·easier·원래 예시), 흐름 패널, 익명 사용자 |
| 묶음 2 | #14 | SQLite 저장, 결과 버전·저장, 내 작업·결과물, 문서 내려받기 |
| 묶음 3a | #15 | 결과 섹션·블록, 문구 수정, 미확인 정보 보완 |
| 묶음 3b | #16 | 근거 자료 검토(샘플), 결과 이미지(Mock SVG), 파일 저장소 |
| 디자인 피드백 | #17 | 생성 중·생성 실패 화면, 최신 아님 배너, 이미지 상자, 모드 설명, WBS·`scripts/wbs.py` |
| 묶음 4 | #18 | 다음 과제로 이어가기(이전 결과의 기준 가져오기·빼기) |
| 인수인계 | #19 | 이 문서, PR마다 갱신하는 규칙(`CLAUDE.md` 개발 방식) |
| 실제 Claude 연결 | #20 | `ClaudeProvider`(공식 SDK, 구조화 출력·시스템 캐시·거절 시 서버 측 대체), `PROVIDER=claude`·`CLAUDE_MODEL`·`CLAUDE_EFFORT`, `scripts/claude_smoke.py` |
| 무료 배포 설정 | #21 | `render.yaml`(렌더 Free), `vercel.json` rewrites, `docs/DEPLOY.md` |
| 배포 완료 기록 | #22 | 실제 주소, WBS 5.1·5.2 완료 |
| README 정리 | #23 | 바로 보기 주소, 된 것, 남은 일(맡을 사람·상의할 점) |
| 외부 전송 보호 | #24 | 외부 AI로 나가는 프롬프트의 개인정보 가림(주민번호·카드·계좌·전화·이메일), 비공개 항목(정책 `private_fields` + 사용자 체크) 제외, 세션 생성 때 외부 전송 고지 동의, 비공개만 바뀌어도 결과 최신 아님, 기준 표 'AI에 보내지 않음' 표시 |
| 프롬프트 주입 기본 방어 | #25 | 바깥 값을 `<user_input>` 태그로 감싸고 system에 자료 취급 지시, AI 출력에 system 줄이 그대로 섞이면 422 |
| 단계별 모델 라우팅(기본 꺼짐) | #26 | `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`(JSON)로 단계마다 모델·노력을 다르게(`providers/routing.py`, `RoutedProvider`). 비어 있으면 모든 단계가 `CLAUDE_MODEL`·`CLAUDE_EFFORT` |
| 하네스 성능 로드맵·인수 안내(README) | #26 | `docs/HARNESS-ROADMAP.md`(측정 → 라우팅 → 선택 단계), README "인수 기업이 알아야 할 것" |
| AI 동시 호출 상한 | #27 | LLM·이미지 호출을 자리 수(`AI_MAX_CONCURRENT_CALLS`, 기본 4)로 묶는다(`providers/limit.py`). 자리를 `AI_QUEUE_WAIT_SECONDS`(기본 10초) 안에 못 얻으면 503 + `Retry-After`, 세션은 그대로(생성도 `FAILED`가 되지 않는다). 메모리·스레드 부하가 사용자 수가 아니라 설정값에 묶인다 |
| 병렬 생성(기본 꺼짐)·설계 고민 기록(README) | #28 | 정책 `parallel_generation`으로 결과 항목을 조각으로 나눠 `generate_part`를 동시에 부르고 코드로 합친다(`harness/parallel.py`). 끝난 조각은 세션 캐시(프롬프트 해시)에 남아 실패한 조각만 다시 부른다. 모든 과제에서 꺼 둠. README "설계 고민 기록"(메모리·동시 호출·n중 파이프라인·병렬·종합 방식), 로드맵 0단계 측정표·3-1절 |
| 측정 준비(비용 0) | #29 | trace `duration_ms`(호출마다 걸린 시간), `evals.play_questions`(실제 모델용: 계획 어긋남을 센다), 과제마다 `quick-skip.yaml`, 측정 도구 `scripts/measure.py`(과제×시나리오×한 번 호출·병렬×반복 → `rows.csv`·`summary.md`, 기본 Mock, 실제 모델은 `--budget-usd` 필수) |
| 시연·평가 준비 | #30 | `docs/DEMO.md`(시연 순서·질문 대비), `docs/EVALUATION.md`(14장 지표를 무엇으로 재나·사용성 테스트·비교 실험), 평가 통계 `scripts/session_stats.py`(`app/harness/stats.py`, 저장소 `list_all`) |
| 결과 문서 내보내기 | #31 | 결과·저장 완료·버전 보기의 '문서 내려받기' 메뉴: PDF(인쇄 창 'PDF로 저장')·Word(.docx)·HTML. 요청 예시를 한글 북백으로 |
| 작업·결과물 정리 | #32 | 내 작업: 작업 삭제(확인 대화상자)·이름 바꾸기, 결과물: 결과물에서 빼기. 내려받는 파일 이름은 작업 이름 |
| 데이터 보존(Neon Postgres) | #33 | STORE=postgres(세션·결과 이미지), 렌더가 다시 시작해도 남는다. 계약 테스트는 내장 Postgres(pgserver) |
| BAZE 게이트웨이(Claude·GPT) | #34 | 키 하나로 실제 Claude·GPT 호출. `PROVIDER=openai`(`OpenAIProvider`, Chat Completions strict 스키마), 게이트웨이 주소·키 설정 `CLAUDE_BASE_URL`·`CLAUDE_API_KEY`·`OPENAI_*`(`config.provider_options`). 측정·스모크 스크립트가 두 제공자 모두 돈다. 절차 `docs/DEPLOY.md` "BAZE" |
| 렌더에서 실제 AI | #35 | `render.yaml`: `PROVIDER`는 대시보드에서(`sync: false`), BAZE 주소·모델은 파일, 키 `CLAUDE_API_KEY`·`OPENAI_API_KEY`는 대시보드에만 |
| IR 피치덱 과제 | #36 | 다섯 번째 과제 `ir_pitch`(투자자 발표용 슬라이드별 원고). 결과 스키마(슬라이드 5~12장: 종류·제목 문장·원고, 한 줄 소개·투자 요청·예상 질문), 검증(투자 요청 없음=오류, 문제·해결·투자 요청 슬라이드 누락·근거 없는 기업가치·시장 규모=경고), 질문 9개(투자 유치 목적이 스탠다드에서도 물어지게 순서 조정), 희망 투자 금액·현재 매출은 처음부터 AI에 보내지 않음, 이전 과제에서 아이디어·고객·문제·수익 이어받기. 홈 카드 5개(홀수면 마지막 카드가 한 줄) |
| 테스트 케이스(TC2·TC4~TC8) | #37 | 제출용 테스트 케이스 = 인수 테스트 + 엑셀. `backend/tests/acceptance/test_tcN_*.py`(사용자가 API로 하는 순서, 공통 흐름 `flow.py`)·`frontend/src/acceptance/tc8.test.ts`. 원본 `docs/test-cases.yaml` → `scripts/test_cases.py run`이 자동 테스트를 돌려 `docs/TEST-CASES.xlsx`에 결과·통과·실행일을 채운다(수동 행은 `manual_result`·`ran_on`). `tests/test_test_cases_doc.py`가 참조 위치·엑셀 행을 확인. 렌더 실제 Claude로 IR 1회 확인(TC4-4) 뒤 슬라이드 종류를 한국어 이름으로 쓰게 지침 수정 |
| 화면 전환 계산 시간(TC1) | #38 | 버튼 → 다음 화면의 상태 갱신·화면 판단(reducer → screenModel·needsLoad, 네트워크·렌더 제외)을 화면 전환 15개(실제 앱에서 가능한 시작 상태 → 이동·요청·응답, 도착 화면·남은 불러오기 없음 확인)마다 중앙값으로 재는 인수 테스트 `frontend/src/acceptance/tc1.test.ts`(기준 0.5ms, 측정 도우미 `testing/timing.ts`). 시작 전 측정 중앙값 약 0.0013ms(개발 PC)라 코드 최적화는 하지 않았다 |
| 제공자 비교(TC3) | #39 | 같은 평가 시나리오를 제공자마다 돌려 나란히 비교하는 `scripts/compare_providers.py`(`measure.compare`·`write_comparison`, 예산은 제공자마다 나눔, 실제 제공자는 `--budget-usd` 필수), 실행마다 결과 글(`documents/`)과 제공자별 합계 표(`provider_totals`). 2026-11-04 실제 실행(승인): Claude Sonnet 5.5 vs GPT-6.1 terra, 시나리오 10개씩 모두 완료·실패 0, 추정 $0.41 vs $0.11. 결과·관찰 `docs/PROVIDER-COMPARISON.md` |
| 재고 관리 핵심 | #40 | 설계(`docs/superpowers/specs/2026-11-08-inventory-design.md`)·IA 원본(`design/2026-11-05-ia-inventory-proposal/`), owner별 재고 묶음, 원장 기반 수량, 품목·거래처·설정·보충 기준·하루 마감(이상 수량 확인) API |
| 재고 주문·자동 주문·AI 추천 | #42 | 모의 거래처(`SupplierProvider`, `mock_outcome`로 접수·가격 변동·품절·접수 불명), 수동 주문(멱등 `request_id`)·재조회·일부 입고(`already_counted`)·보류(해결), 자동 주문(마감 직후, 동의·배송지·1회/품목별 월 한도·오래된 실사·접수 불명은 보류, 가격 변동·품절 보류 중인 품목은 멈춤), AI 보충 기준 추천(확인 전 → 적용). API 7개 + 마감 응답 `auto_orders` |
| QA 피드백 반영(2026-11-08) | #43 | QA(김혜수) FAIL 7건 중 4건 수정: 직접 답변·답 고치기 서버 길이 상한 1,200자(PERF-020), 배포(`DEBUG=false`)에서 `/docs`·`/redoc`·`/openapi.json` 닫기(SEC-014), 보완 정보 비공개 체크·저장 완료 내려받기 버튼 배치(UI-004), 보내기 전 입력 초안(직접 답변·답 고치기·문구 고치기, 결과 버전별)을 브라우저에 남기기(UI-005). 고치지 않은 것: SEC-001(가림은 외부 AI 전송에만, 본인 화면은 원문), SEC-006(세션 id는 비밀 아님, 열람은 owner 확인 — SEC-005 PASS), PERF-002(렌더 무료 서버 깨우기, 재측정). 배포 DB의 QA 측정 세션(익명 ID `qa-perf-20261108`)은 두고 `session_stats.py --exclude-owner`로 뺀다 |

계획 문서는 `docs/superpowers/plans/`에 묶음마다 있다(무엇을 왜 그렇게 정했는지는 각 계획의 "결정 사항").

## 다음 할 일 (WBS 순서)

**재고 관리 묶음**: #40 재고 핵심 → #42 주문·자동 주문·AI 기준 추천 → 화면 두 PR(디자인은 기능을 더 발전시킨 뒤 받는다).

**끝난 묶음(2026-11-04 요청, 테스트 케이스 = 자동 테스트 + `docs/TEST-CASES.xlsx`)**: #36 IR 과제(완료) → #37 테스트 케이스 문서와(완료) TC2(외부 메모리 동적 참조 = README '설계 고민 기록' 1번: 무상태 처리 + 세션 저장소 + 동시 호출 상한)·TC4(과제별 하네스, IR 포함 5개)·TC5(호출 상한 503, 세션 불변)·TC6(모드별 컨텍스트)·TC7(이어가기 오류: 404·없는 버전·미리보기 실패·빼기·비공개 유지)·TC8(결과 생성·PDF/Word/HTML) → #38 TC1(화면 전환 계산 0.5ms 이하, 완료) → #39 TC3(OpenAI vs Claude 같은 시나리오 비교, 완료). 남은 것: 수동 TC8-7('PDF로 저장'을 실제 브라우저에서 확인 → YAML `manual_result`·`ran_on` → `scripts/test_cases.py run`).

0. **Neon 가입·`DATABASE_URL` 입력(사용자)** — `docs/DEPLOY.md` "Neon 연결". PR #33 머지 전에 렌더 Environment에 넣는다(안 넣으면 서버가 시작하지 못한다). **후순위: 로그인(다른 기기에서 내 작업)·결과물 공유 링크**(WBS 4.10·4.11).
1. **디자인 검수(디자이너)** — WBS 3.3·3.4
   - 모바일 390px 화면 확인, `/preview`를 html.to.design으로 피그마에 가져와 다듬기(`design/README.md`).
   - 수정본이 오면 `design/YYYY-MM-DD-…/`에 받은 그대로 넣고 직전 원본과 비교해 바뀐 화면만 반영한다(PR #17이 본보기).
2. **배포는 끝났다(2026-10-18)** — WBS 5.1·5.2. 버셀 https://ax-platform-5.vercel.app (main 머지마다 자동 배포), 렌더 https://ax-coaching-api.onrender.com (`render.yaml`, main 머지마다 자동 배포). 절차·한계는 `docs/DEPLOY.md`.
3. **시연 전 확인** — 몇 분 전에 앱을 열어 렌더를 깨운다(15분 무요청이면 잠들고 깨는 데 약 1분). 데이터는 Neon에 있어 다시 시작해도 남는다(Neon도 한동안 쓰지 않으면 잠들어 첫 요청이 몇 초 늦다). 오래 보관할 결과는 '문서 내려받기' — PDF·Word·HTML.
4. **실제 AI 연결** — WBS 6.1~6.3
   - LLM 어댑터는 Claude(`app/providers/claude.py`)·GPT(`app/providers/openai_chat.py`) 둘 다 준비됐고 BAZE 게이트웨이로 실제 호출을 확인했다(2026-11-03, `docs/DEPLOY.md` "BAZE"). 배포(렌더)는 대시보드 `PROVIDER`로 켜고 끈다(켜면 공개 주소의 생성마다 BAZE 과금, 테스트가 끝나면 `mock`으로). 개발자 로컬 `.env`는 BAZE로 실제 호출을 켤 수 있다. 테스트는 계속 Mock·가짜 응답(네트워크 없음)이다.
   - 인수하는 회사가 켤 때(실제 호출·모델 선택·비용은 그쪽이 정한다, 키는 커밋 금지):
     - `backend/.env`에 `PROVIDER=claude`와 `ANTHROPIC_API_KEY=…`를 넣는다(키가 없으면 서버 시작 때 실패한다). 모델·노력은 `CLAUDE_MODEL`(기본 `claude-opus-5-5`)·`CLAUDE_EFFORT`(기본 `medium`).
     - 세션 하나 확인(그쪽용 스크립트): `uv run --directory backend python ../scripts/claude_smoke.py product_planning "외국인 관광객 선물용 한글 북백"`(진단 → '아직 모르겠어요' 한 번 → 생성, 단계별 모델·토큰 출력). `generate`의 `output_tokens`가 상한 `MAX_TOKENS`(16000)에 가까우면 잘림(`ProviderOutputError`)이 나기 쉬우니 상한이나 결과 분량을 조정한다.
     - 참고 단가(1M 토큰당 입력/출력): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50.
   - 이미지: `ImageProvider` 구현(`app/providers/image.py` 계약). 근거 자료: `BaseHarness.find_evidence`만 웹 검색으로 바꾼다.
   - 과제별 하네스 튜닝(준비도 기준·가중치·프롬프트)은 시나리오(`evals/*.yaml`)로 측정하며 정한다.
   - 실제 호출을 켜면 동시 호출 상한(`AI_MAX_CONCURRENT_CALLS`·`AI_QUEUE_WAIT_SECONDS`)을 서버 메모리와 API 사용 한도(분당 요청)에 맞춘다. 상한은 프로세스 하나 기준이다.
5. **인수 팀(또는 팀이 비용을 내서): 로드맵 0단계 측정 → 라우팅·병렬 생성 설정** — `uv run --directory backend python ../scripts/measure.py --provider claude --budget-usd 2`(측정 도구, 상한 필수)로 평가 시나리오를 돌려 `docs/HARNESS-ROADMAP.md` 0단계 표(병렬 생성 측정표 포함)를 채운 뒤, 필요할 때만 `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`나 과제 정책의 `parallel_generation`을 켠다. 병렬이 어긋나면 '미리 모아 두고 한 번에 종합'(설계 문서 7장)을 구현한다.
6. **평가·발표** — WBS 7.1·7.2 (기획서 14장 지표).
   - 시연은 `docs/DEMO.md` 순서대로(시연 10분 전 렌더 깨우기, 시크릿 창, `/preview` 예비 탭).
   - 사용성 테스트는 비용 0으로 지금 할 수 있다: 로컬 `STORE=sqlite`로 띄우고 참가자 5~8명 → `scripts/session_stats.py`로 과제별 지표 표(필수정보 충족률·이탈률·답한 질문·채택률 등). 절차·설문은 `docs/EVALUATION.md` 2장.
   - 비교 실험(자유 프롬프트·긴 폼·적응형)은 실제 모델 비용과 긴 폼 화면이 필요하다(3장).

## 개인 계정·키·로컬 데이터 (인수 시 교체·삭제)

프로토타입 개발·시연은 개발자 개인 계정과 키로 한다. **키 값은 저장소에 절대 넣지 않는다**(각 서비스 대시보드의 환경 변수나 git에서 빠진 `backend/.env`에만 둔다). 인수할 때 아래 표를 차례로 처리한다.

| 항목 | 어디에 있나 | 지금(개발자 개인) | 인수 시 할 일 |
|---|---|---|---|
| GitHub 저장소 | `kimcheolhui9846/ax_platform_5` | 개인 계정 | 저장소 이전(Transfer)이나 인수 기업 쪽으로 복제 |
| 렌더 서비스 `ax-coaching-api` (https://ax-coaching-api.onrender.com) | render.com 개인 계정(Free) | 개인 서비스, Mock·데이터 휘발 | 인수 기업 계정에서 `render.yaml`로 새로 만들고 개인 서비스 삭제. 주소가 바뀌면 `frontend/vercel.json`의 `rewrites` 교체 |
| 버셀 프로젝트 `ax-platform-5` (https://ax-platform-5.vercel.app) | vercel.com 개인 계정(Hobby) | 개인 프로젝트 | 인수 기업 계정에서 새로 가져오고 개인 프로젝트 삭제 |
| BAZE API 키(`CLAUDE_API_KEY`·`OPENAI_API_KEY`) | 로컬 `backend/.env`(git 제외) | 개인 키(BAZE 개인 계정 과금) | BAZE에서 개인 키 폐기, 인수 기업 키로 교체 |
| Anthropic API 키 `ANTHROPIC_API_KEY` | 로컬 `backend/.env`(git 제외) 또는 렌더 환경 변수 | 개인 키(연결 확인용, 기본 `PROVIDER=mock`이라 호출되지 않음) | 콘솔에서 개인 키 폐기(revoke), 인수 기업 키로 교체 |
| 렌더·버셀 API 토큰(만들었다면) | 각 대시보드 | 개인 토큰 | 폐기 |
| `frontend/vercel.json`의 `rewrites` 주소 | 저장소 | 개인 렌더 서비스 주소 | 인수 기업 렌더 주소로 교체 |
| 로컬 DB·이미지 `backend/data/` | 개발자 PC(git 제외) | 테스트 데이터 | 삭제해도 된다(넘길 데이터 없음) |
| Neon Postgres 프로젝트 (세션·이미지, `DATABASE_URL`) | neon.tech 개인 계정(Free) | 개인 프로젝트, 테스트 데이터 | 인수 기업 계정에서 새 프로젝트로 교체하고 개인 프로젝트 삭제. 연결 문자열 폐기(Neon에서 비밀번호 재설정), 렌더 `DATABASE_URL` 교체 |
| 익명 사용자 ID | 각 브라우저 `localStorage['ax.client-id']` | 브라우저마다 | 로그인 붙일 때 `current_owner` 교체(`CLAUDE.md`) |

## 남겨 둔 것·알려진 한계

- **정밀 모드가 더 깊게 묻지 않는다(하네스 튜닝 과제, WBS 6.2)**: 준비도 기준(`readiness_threshold` 0.7)이 상한보다 먼저 차서, 실제 질문 수(빠른/스탠다드/정밀)가 사업계획·상품기획 3/4/4, 브랜딩·마케팅 3/3/3, IR 3/5/5다. 정밀 상한 10에는 어느 과제도 닿지 않는다. 모드별로 준비도 기준을 달리 두는 등 정책을 튜닝할 때 TC6-3·TC4-3 기대값도 같이 고친다.
- **금지어 경고의 오탐(하네스 튜닝 과제, WBS 6.2)**: IR의 '근거 없는 기업가치·시장 규모' 경고(`term_rule`)가 "시장 규모 수치는 근거를 확인한 뒤 넣겠습니다"처럼 쓰지 않겠다는 문장에도 걸린다(#39 비교에서 Claude 2건·GPT 1건 모두 이 경우). 숫자와 함께 쓰인 경우만 보게 하는 등 규칙을 다듬을 때 시나리오로 확인한다. 2026-11-08 QA(PERF-021)도 사업계획의 '매출 전망' 경고가 부정문에 걸린 것으로 보고했다.
- 테스트 케이스 엑셀의 TC8-7(실제 브라우저 'PDF로 저장')은 수동 행이라 직접 확인한 뒤 `docs/test-cases.yaml`에 `manual_result`·`ran_on`을 적고 `run`을 다시 돌린다.
- IR 피치덱은 슬라이드 원고를 결과 카드(제안 카드에 슬라이드 순서대로)와 `full_text`에 싣도록 지침을 뒀다. 디자인된 슬라이드 파일(.pptx)은 만들지 않는다. #39 비교에서 Claude·GPT 모두 슬라이드 9~10장을 한국어 슬라이드 이름으로 카드에 실었다(`docs/PROVIDER-COMPARISON.md`, Mock은 자리표시 본문이라 '핵심 슬라이드가 빠졌습니다' 경고가 뜬다).
- 이어가기는 이전 결과의 사실·보완 정보를 새 과제의 **필드**로만 옮긴다. 새 과제의 보완 항목(`supplement_fields`)으로 옮기는 것은 하지 않았다(브랜딩처럼 겹치는 필드가 적은 과제는 가져오는 값이 적다).
- 외부 전송 보호(#24)가 막지 못하는 것:
  - 자유 문장 속 사업 비밀은 패턴이 없어 자동으로 못 가린다(고지와 비공개 표시로 안내만 한다).
  - 주입: 태그·지시가 있어도 모델이 따를 수 있다, 바꿔 쓴 유출은 못 찾는다, 꺾쇠 닮은 전각 문자(＜＞·〈〉)는 이스케이프하지 않는다, 웹 검색 자료도 `block`과 같은 검사를 거쳐야 한다(#25는 기본 방어만).
  - 서버 DB는 평문이고, 로그인 없는 익명 ID이며, 보관 기간·삭제 기능이 없다.
  - 외부 AI 업체의 데이터 보관·학습 정책 확인과 계약, 개인정보 처리방침은 인수 기업 몫이다.
  - 이어가기로 가져온 이전 결과의 제목·요약(`_context.md`)은 정규식 가림만 거친다(비공개 이름을 따로 적용하지 않는다).
  - 구분 없는 16자리(앞자리 3–6)는 모두 가린다(Luhn 검사 없이. 주문번호 오탐 허용).
  - 외부 전송 동의 기능 이전에 만든 세션은 동의 기록이 없다(무료 서버의 Neon 데이터는 개인 테스트 데이터라 프로젝트째 지워도 됨, 로컬 DB도 같다).
- trace에 요청 모델·응답 시간이 없다(측정 전에 더할 것). 캐시 토큰은 `usage`에 있다. 요청 모델은 설정에서 단계별로 읽고, 실패한 호출은 `model`이 비어 있다. 응답 시간 기록은 인수 팀이 `_call`에 더한다.
- '생성 취소'는 없다(생성은 서버가 끝까지 처리하는 요청이라 취소해도 새 버전이 생긴다).
- 생성 뒤 다른 단계가 실패하면 만든 이미지 파일이 남을 수 있다(배포 때 정리 방식을 정한다).
- 질문 단계 화면의 진행 표시는 "질문 2/5"(상한)로 둔다. 디자인의 "예시 질문 진행"은 프로토타입 문구.

## 작업 방식 (새 세션이 따를 절차)

1. main에서 `task/<번호>-<이름>` 브랜치(다음 번호는 PR 번호와 같게, 지금은 36 다음).
2. 계획: `superpowers:writing-plans`로 `docs/superpowers/plans/YYYY-MM-DD-<이름>.md`(Task마다 파일·인터페이스·테스트 코드·커밋 메시지). 커밋.
3. 실행: `superpowers:subagent-driven-development`. Task마다 구현 서브에이전트 → 리뷰 서브에이전트(스펙·품질) → 지적이 있으면 같은 구현자에게 고치게 하고 범위를 좁힌 재리뷰. 마지막에 브랜치 전체 리뷰(가장 강한 모델) → 수정 한 번 → 재리뷰.
   - **리뷰 지적은 미루지 않고 전부 고친다**(튜닝 값만 예외). 계획 코드가 틀렸으면 계획을 고쳐 따른다.
   - 진행 기록은 `.superpowers/sdd/<계획 이름>/progress.md`(git 제외). 끝나면 그 폴더를 지운다.
4. 브라우저 확인(아래 "환경 팁") → WBS 갱신(`scripts/wbs.py`) → 이 문서 갱신 → 푸시 → PR(`gh pr create`).
5. **머지는 사용자가 한다.** 자동 권한 판정이 `gh pr merge`를 막으므로 사용자에게 `! gh pr merge <번호> --squash --delete-branch`를 부탁하고, 머지 뒤 `git checkout main && git pull`.
6. 커밋·PR에 AI 공동저자·생성 표기를 넣지 않는다. git 신원 `kim cheol hui <144594976+kimcheolhui9846@users.noreply.github.com>`. `backend/.env`는 읽거나 고치지 않는다. 사용자에게는 한국어로 답한다.

## 환경 팁 (Windows)

- 백엔드 서버: `uv run --directory backend python -m uvicorn app.main:app --port 8000`(uvicorn.exe 직접 실행이 막힐 수 있다).
- 브라우저 확인용 임시 DB: `STORE=sqlite DATABASE_PATH=<스크래치>/sessions.db ASSET_DIR=<스크래치>/assets DEBUG=true`를 앞에 붙여 띄우고, 끝나면 스크래치 폴더·`.playwright-mcp/`를 지운다.
- 한글 본문으로 API를 부를 때 Git Bash `curl`은 깨진다. 짧은 Python 스크립트(`urllib.request`, `python -I`)로 부른다.
- 브라우저에서 익명 사용자 ID를 바꾸려면 `localStorage['ax.client-id']`를 넣고 **페이지를 새로고침**한다(API 클라이언트가 처음 읽은 값을 쓴다).
- 생성 중·실패 화면을 보려면 Playwright `page.route('**/generate', …)`로 지연·502를 만든다(페이지 안 `fetch` 바꿔치기는 API 클라이언트에 안 먹는다).
- `docs/WBS.xlsx`가 엑셀에 열려 있으면 `scripts/wbs.py`가 저장하지 못한다. 사용자에게 닫아 달라고 한다.
- 서브에이전트 스크립트: `C:/Users/00/.claude/plugins/cache/superpowers-marketplace/superpowers/6.2.0/skills/subagent-driven-development/scripts/`(`sdd-workspace`, `task-brief`, `review-package`).
