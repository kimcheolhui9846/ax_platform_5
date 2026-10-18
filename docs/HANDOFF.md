# 작업 인수인계 (HANDOFF)

세션이 바뀌어도 이 문서만 읽고 이어서 일할 수 있게 둔다. **PR을 머지할 때마다 같은 PR에서 "지금 상태"와 "다음 할 일"을 고친다**(WBS와 같이).

- 기준일: 2026-10-18
- main: `ec4080f` (PR #18까지 머지)
- 테스트: 백엔드 462 passed, 프론트 410 passed, 빌드 OK

새 세션에서는 "docs/HANDOFF.md 읽고 이어서 해"라고 하면 된다. 프로젝트 규칙은 `CLAUDE.md`, 팀 공유용 작업 현황은 `docs/WBS.xlsx`다.

## 지금 상태

디자인 V2 화면 개발(묶음 0~4)과 디자이너 피드백 반영이 끝났다. 모든 AI 호출은 아직 Mock이다(비용 0).

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

계획 문서는 `docs/superpowers/plans/`에 묶음마다 있다(무엇을 왜 그렇게 정했는지는 각 계획의 "결정 사항").

## 다음 할 일 (WBS 순서)

1. **디자인 검수(디자이너)** — WBS 3.3·3.4
   - 모바일 390px 화면 확인, `/preview`를 html.to.design으로 피그마에 가져와 다듬기(`design/README.md`).
   - 수정본이 오면 `design/YYYY-MM-DD-…/`에 받은 그대로 넣고 직전 원본과 비교해 바뀐 화면만 반영한다(PR #17이 본보기).
2. **프론트 버셀 연결(사용자)** — WBS 5.1. vercel.com에서 한 번:

   | 항목 | 값 |
   |---|---|
   | Import | GitHub `kimcheolhui9846/ax_platform_5` |
   | Root Directory | `frontend` |
   | 빌드 설정 | `frontend/vercel.json`이 정한다(`npm ci` / `npm test && npm run build` / `dist`) |
   | 환경 변수 | 지금은 없음. 백엔드를 붙일 때 정한다(아래 2번) |

3. **백엔드 렌더 배포** — WBS 5.2. 먼저 정할 것:
   - 저장 디스크: SQLite 파일(`DATABASE_PATH`)과 이미지 폴더(`ASSET_DIR`)를 남길 영속 디스크.
   - 프론트와 연결: 백엔드 CORS(버셀 도메인) + `VITE_API_BASE`, 또는 `vercel.json` `rewrites`로 `/api/:path*`를 렌더로 넘겨 같은 출처(이때 `VITE_API_BASE`는 비운다).
   - 서버 프로세스는 하나(세션 잠금이 프로세스 안 잠금이다).
4. **실제 AI 연결** — WBS 6.1~6.3
   - `app/providers/`에 Claude `LLMProvider` 구현, `factory.py`에 등록(`CLAUDE.md` "비용" 절). 테스트는 계속 Mock.
   - 이미지: `ImageProvider` 구현(`app/providers/image.py` 계약). 근거 자료: `BaseHarness.find_evidence`만 웹 검색으로 바꾼다.
   - 과제별 하네스 튜닝(준비도 기준·가중치·프롬프트)은 시나리오(`evals/*.yaml`)로 측정하며 정한다.
5. **평가·발표** — WBS 7.1·7.2 (기획서 14장 지표).

## 남겨 둔 것·알려진 한계

- 이어가기는 이전 결과의 사실·보완 정보를 새 과제의 **필드**로만 옮긴다. 새 과제의 보완 항목(`supplement_fields`)으로 옮기는 것은 하지 않았다(브랜딩처럼 겹치는 필드가 적은 과제는 가져오는 값이 적다).
- '생성 취소'는 없다(생성은 서버가 끝까지 처리하는 요청이라 취소해도 새 버전이 생긴다).
- 생성 뒤 다른 단계가 실패하면 만든 이미지 파일이 남을 수 있다(배포 때 정리 방식을 정한다).
- 질문 단계 화면의 진행 표시는 "질문 2/5"(상한)로 둔다. 디자인의 "예시 질문 진행"은 프로토타입 문구.

## 작업 방식 (새 세션이 따를 절차)

1. main에서 `task/<번호>-<이름>` 브랜치(다음 번호는 PR 번호와 같게, 지금은 19 다음).
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
