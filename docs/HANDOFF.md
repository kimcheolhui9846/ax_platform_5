# 작업 인수인계 (HANDOFF)

세션이 바뀌어도 이 문서만 읽고 이어서 일할 수 있게 둔다. **PR을 머지할 때마다 같은 PR에서 "지금 상태"와 "다음 할 일"을 고친다**(WBS와 같이).

- 기준일: 2026-10-18
- main: `427793c` (PR #23까지 머지)
- 테스트: 백엔드 545 passed, 프론트 437 passed, 빌드 OK
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

계획 문서는 `docs/superpowers/plans/`에 묶음마다 있다(무엇을 왜 그렇게 정했는지는 각 계획의 "결정 사항").

## 다음 할 일 (WBS 순서)

1. **디자인 검수(디자이너)** — WBS 3.3·3.4
   - 모바일 390px 화면 확인, `/preview`를 html.to.design으로 피그마에 가져와 다듬기(`design/README.md`).
   - 수정본이 오면 `design/YYYY-MM-DD-…/`에 받은 그대로 넣고 직전 원본과 비교해 바뀐 화면만 반영한다(PR #17이 본보기).
2. **배포는 끝났다(2026-10-18)** — WBS 5.1·5.2. 버셀 https://ax-platform-5.vercel.app (main 머지마다 자동 배포), 렌더 https://ax-coaching-api.onrender.com (`render.yaml`, main 머지마다 자동 배포). 절차·한계는 `docs/DEPLOY.md`.
3. **시연 전 확인** — 몇 분 전에 앱을 열어 렌더를 깨운다(15분 무요청이면 잠들고 깨는 데 약 1분). 다시 시작하면 데이터가 지워진다(보관은 '문서 내려받기').
4. **실제 AI 연결** — WBS 6.1~6.3
   - LLM 어댑터는 준비됐다(`app/providers/claude.py`). 이 프로토타입은 비용 0을 지키므로 `PROVIDER`는 `mock`으로 둔다. 테스트는 계속 Mock·가짜 응답(네트워크 없음)이다.
   - 인수하는 회사가 켤 때(실제 호출·모델 선택·비용은 그쪽이 정한다, 키는 커밋 금지):
     - `backend/.env`에 `PROVIDER=claude`와 `ANTHROPIC_API_KEY=…`를 넣는다(키가 없으면 서버 시작 때 실패한다). 모델·노력은 `CLAUDE_MODEL`(기본 `claude-opus-5-5`)·`CLAUDE_EFFORT`(기본 `medium`).
     - 세션 하나 확인(그쪽용 스크립트): `uv run --directory backend python ../scripts/claude_smoke.py product_planning "집들이 선물용 수제 향초"`(진단 → '아직 모르겠어요' 한 번 → 생성, 단계별 모델·토큰 출력). `generate`의 `output_tokens`가 상한 `MAX_TOKENS`(16000)에 가까우면 잘림(`ProviderOutputError`)이 나기 쉬우니 상한이나 결과 분량을 조정한다.
     - 참고 단가(1M 토큰당 입력/출력): Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50.
   - 이미지: `ImageProvider` 구현(`app/providers/image.py` 계약). 근거 자료: `BaseHarness.find_evidence`만 웹 검색으로 바꾼다.
   - 과제별 하네스 튜닝(준비도 기준·가중치·프롬프트)은 시나리오(`evals/*.yaml`)로 측정하며 정한다.
5. **평가·발표** — WBS 7.1·7.2 (기획서 14장 지표).

## 개인 계정·키·로컬 데이터 (인수 시 교체·삭제)

프로토타입 개발·시연은 개발자 개인 계정과 키로 한다. **키 값은 저장소에 절대 넣지 않는다**(각 서비스 대시보드의 환경 변수나 git에서 빠진 `backend/.env`에만 둔다). 인수할 때 아래 표를 차례로 처리한다.

| 항목 | 어디에 있나 | 지금(개발자 개인) | 인수 시 할 일 |
|---|---|---|---|
| GitHub 저장소 | `kimcheolhui9846/ax_platform_5` | 개인 계정 | 저장소 이전(Transfer)이나 인수 기업 쪽으로 복제 |
| 렌더 서비스 `ax-coaching-api` (https://ax-coaching-api.onrender.com) | render.com 개인 계정(Free) | 개인 서비스, Mock·데이터 휘발 | 인수 기업 계정에서 `render.yaml`로 새로 만들고 개인 서비스 삭제. 주소가 바뀌면 `frontend/vercel.json`의 `rewrites` 교체 |
| 버셀 프로젝트 `ax-platform-5` (https://ax-platform-5.vercel.app) | vercel.com 개인 계정(Hobby) | 개인 프로젝트 | 인수 기업 계정에서 새로 가져오고 개인 프로젝트 삭제 |
| Anthropic API 키 `ANTHROPIC_API_KEY` | 로컬 `backend/.env`(git 제외) 또는 렌더 환경 변수 | 개인 키(연결 확인용, 기본 `PROVIDER=mock`이라 호출되지 않음) | 콘솔에서 개인 키 폐기(revoke), 인수 기업 키로 교체 |
| 렌더·버셀 API 토큰(만들었다면) | 각 대시보드 | 개인 토큰 | 폐기 |
| `frontend/vercel.json`의 `rewrites` 주소 | 저장소 | 개인 렌더 서비스 주소 | 인수 기업 렌더 주소로 교체 |
| 로컬 DB·이미지 `backend/data/` | 개발자 PC(git 제외) | 테스트 데이터 | 삭제해도 된다(넘길 데이터 없음) |
| 렌더 Free의 세션·이미지 | 렌더 서버(디스크 없음) | 다시 시작하면 지워짐 | 넘길 데이터 없음 |
| 익명 사용자 ID | 각 브라우저 `localStorage['ax.client-id']` | 브라우저마다 | 로그인 붙일 때 `current_owner` 교체(`CLAUDE.md`) |

## 남겨 둔 것·알려진 한계

- 이어가기는 이전 결과의 사실·보완 정보를 새 과제의 **필드**로만 옮긴다. 새 과제의 보완 항목(`supplement_fields`)으로 옮기는 것은 하지 않았다(브랜딩처럼 겹치는 필드가 적은 과제는 가져오는 값이 적다).
- 외부 전송 보호(#24)가 막지 못하는 것:
  - 자유 문장 속 사업 비밀은 패턴이 없어 자동으로 못 가린다(고지와 비공개 표시로 안내만 한다).
  - 프롬프트 주입(사용자 입력이 지시처럼 행동)은 시스템·사용자 블록 분리 외에 출력 검증을 강화하지 않았다.
  - 서버 DB는 평문이고, 로그인 없는 익명 ID이며, 보관 기간·삭제 기능이 없다.
  - 외부 AI 업체의 데이터 보관·학습 정책 확인과 계약, 개인정보 처리방침은 인수 기업 몫이다.
  - 이어가기로 가져온 이전 결과의 제목·요약(`_context.md`)은 정규식 가림만 거친다(비공개 이름을 따로 적용하지 않는다).
  - 구분 없는 16자리(앞자리 3–6)는 모두 가린다(Luhn 검사 없이. 주문번호 오탐 허용).
  - 외부 전송 동의 기능 이전에 만든 세션은 동의 기록이 없다(무료 서버는 재시작 때 지워짐, 로컬 DB는 지워도 됨).
- '생성 취소'는 없다(생성은 서버가 끝까지 처리하는 요청이라 취소해도 새 버전이 생긴다).
- 생성 뒤 다른 단계가 실패하면 만든 이미지 파일이 남을 수 있다(배포 때 정리 방식을 정한다).
- 질문 단계 화면의 진행 표시는 "질문 2/5"(상한)로 둔다. 디자인의 "예시 질문 진행"은 프로토타입 문구.

## 작업 방식 (새 세션이 따를 절차)

1. main에서 `task/<번호>-<이름>` 브랜치(다음 번호는 PR 번호와 같게, 지금은 24 다음).
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
