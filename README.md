# AX 코칭 플랫폼

창작자가 좋은 프롬프트를 쓰지 못해도, 과제별 적응형 질문으로 아이디어를 구체화해 사업계획·상품기획·브랜딩·마케팅 콘텐츠 결과물로 바꾸도록 돕는 모바일 친화형 AI 코칭 플랫폼입니다. 학교 팀 프로젝트(개발 1명, 디자인 1명)로 만든 **프로토타입**이고, 나중에 다른 기업이 인수해 실제 운영을 정하는 것을 전제로 합니다.

## 바로 보기

| 무엇 | 주소 |
|---|---|
| 앱 | https://ax-platform-5.vercel.app |
| 화면 미리보기 갤러리(모든 화면 상태, 피그마로 가져가는 주소) | https://ax-platform-5.vercel.app/preview |
| API 문서 | https://ax-coaching-api.onrender.com/docs |

- 비용 0으로 운영합니다. AI 응답은 **Mock**(자리표시 글)이라 질문·결과 글이 `[mock] …`처럼 보입니다.
- 백엔드는 렌더 무료 플랜이라 15분 동안 요청이 없으면 잠들고, 처음 열 때 깨어나는 데 1분쯤 걸립니다. 다시 시작하면 저장한 세션이 지워집니다. 시연 몇 분 전에 한 번 열어 두세요.
- 배포는 개발자 개인 계정입니다. 인수 시 교체할 목록은 [`docs/HANDOFF.md`](docs/HANDOFF.md)의 "개인 계정·키·로컬 데이터"에 있습니다.

## 지금까지 된 것

- 과제 4개(사업계획·상품기획·브랜딩·마케팅 콘텐츠)의 적응형 질문 흐름: 모드별 질문 수, '다른 예시 보기', '아직 모르겠어요', 답 고치기
- 결과 문서: 섹션·이미지 상자, 문구 수정, 미확인 정보 보완, 근거 자료 검토(샘플), 버전 저장·내려받기
- 생성 중·생성 실패·결과가 최신이 아님 화면
- 다음 과제로 이어가기(이전 결과의 기준 가져오기)
- 실제 Claude 연결 준비(키만 넣으면 동작, 지금은 Mock)
- 외부 AI로 보내기 전 보호(개인정보 자동 가림, 비공개 항목 제외, 외부 전송 고지·동의)
- 프롬프트 주입 기본 방어(사용자 입력 감싸기, 내부 지침 유출 차단)

## 남은 일 — 팀에서 상의할 것

| 할 일 | 맡을 사람 | 지금 상태 | 상의할 점 |
|---|---|---|---|
| **디자인 검수** — 모바일 390px 화면 확인, `/preview`를 html.to.design으로 피그마에 가져와 다듬기 | 디자이너 | 미리보기 주소 준비됨 | 고칠 화면과 우선순위. 수정본(HTML)을 주면 개발이 바뀐 화면만 반영한다([`design/README.md`](design/README.md)) |
| **AI 품질 튜닝** — 과제별 질문 순서·준비도 기준·프롬프트 다듬기 | 인수 기업 | Mock으로 흐름만 완성 | 실제 모델 호출 비용이 든다. 어떤 모델·노력 수준을 쓸지, 평가 시나리오(`evals/`)로 무엇을 잴지 |
| **실제 AI 호출** — Mock 대신 Claude | 인수 기업 | 어댑터 준비 완료(`PROVIDER=claude` + API 키) | 사용할 모델과 월 예산. 방법은 → 아래 '인수 기업이 알아야 할 것' |
| **결과 이미지 생성** — 지금은 회색 자리표시 이미지 | 인수 기업 | 연결 자리(`ImageProvider`)만 있음 | 이미지 생성 서비스 선택과 비용. 바꾸는 법은 → 아래 '인수 기업이 알아야 할 것' |
| **근거 자료 웹 검색** — 지금은 상품기획 샘플 2건 | 인수 기업 | 바꿀 자리(`find_evidence`)만 있음 | 웹 검색 서비스 선택, 출처 표시·검증 방식. 바꾸는 법은 → 아래 '인수 기업이 알아야 할 것' |
| **데이터 보관** — 지금은 재시작하면 지워짐 | 인수 기업 | 무료 플랜 | 유료 서버·디스크 또는 DB 중 무엇으로 갈지 → 아래 '인수 기업이 알아야 할 것' |
| **보안·개인정보** | 인수 기업 | 보내기 전 거르기·고지 동의 동작(Mock) | AI 업체 계약·처리방침·암호화·보관 기간 등 무엇을 정할지 → 아래 '인수 기업이 알아야 할 것'. 이 표에서는 실제 모델로 주입 공격 평가와 자유 문장 속 비밀 처리를 상의한다 |
| **평가·발표** | 팀 | 예정 | 기획서 14장 지표 중 무엇을 보여 줄지, 시연 시나리오 |

진행 현황은 [`docs/WBS.xlsx`](docs/WBS.xlsx)에 있고, PR을 머지할 때마다 갱신합니다.

## 인수 기업이 알아야 할 것

프로토타입은 비용 0으로 만들었다. 실제로 운영하려면 아래를 정하고 바꾼다. 자세한 절차는 링크한 문서에 있다.

| 무엇 | 지금 | 바꾸는 법 | 문서 |
|---|---|---|---|
| **계정·키** | 배포(버셀·렌더)와 API 키가 개발자 개인 것 | 인수 기업 계정으로 다시 배포(GitHub 저장소 이전, `frontend/vercel.json`의 rewrites 주소를 새 렌더 주소로 교체 포함)하고 개인 키는 폐기 | [`docs/HANDOFF.md`](docs/HANDOFF.md) "개인 계정·키·로컬 데이터", [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| **실제 AI 호출** | Mock(`PROVIDER=mock`) | `PROVIDER=claude` + 환경 변수 `ANTHROPIC_API_KEY`, 모델 `CLAUDE_MODEL`·노력 `CLAUDE_EFFORT`. 먼저 `scripts/claude_smoke.py`로 확인 | [`backend/.env.example`](backend/.env.example) |
| **품질부터 잰다** | 실제 모델로 잰 적 없음 | 과제별 평가 시나리오(`evals/`)를 실제 모델로 돌려 형식 실패·거절·규칙 위반·품질·비용을 잰 뒤에 튜닝·아키텍처를 정한다 | [`docs/HARNESS-ROADMAP.md`](docs/HARNESS-ROADMAP.md) 0단계 |
| **단계별 모델 라우팅** | 구현됨, 기본 꺼짐 | `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`(JSON). 측정 뒤 약한 단계만 올리거나 가벼운 단계를 싸게 | 로드맵 1단계 |
| **디코딩 제약·LoRA** | 금지어 수준 디코딩 제약·LoRA는 하지 않음(출력 형식 강제는 이미 API 구조화 출력으로 함) | 오픈 가중치 모델 서버를 붙일 때 `app/providers/`에 제공자를 더한다. 조건은 로드맵에 | 로드맵 2·3단계 |
| **과제 하네스 튜닝** | 과제 폴더마다 정책·프롬프트·검증·시나리오 | `backend/app/harness/tasks/<과제>/`만 고친다. 고친 뒤 `uv run --directory backend pytest` | [`CLAUDE.md`](CLAUDE.md) "과제 하네스를 고칠 때" |
| **외부 전송 보호** | 개인정보 자동 가림, 비공개 항목, 고지 동의, 프롬프트 주입 기본 방어 | 고지문을 바꾸면 `NOTICE_VERSION`(`backend/app/harness/privacy.py`의 상수)을 올린다. AI 업체와 데이터 보관·학습 계약, 개인정보 처리방침은 인수 기업이 정한다 | HANDOFF "남겨 둔 것·알려진 한계" |
| **데이터 보관** | 무료 렌더라 다시 시작하면 지워짐, SQLite 평문 | 유료 디스크 또는 DB, 저장 시 암호화(키 관리), 로그인 뒤 보관 기간·삭제 | [`docs/DEPLOY.md`](docs/DEPLOY.md) "나중에 바꿀 것" |
| **로그인** | 브라우저 익명 ID(`X-Client-Id`) | `backend/app/api/owner.py`의 `current_owner` 하나만 바꾼다 | CLAUDE.md 하네스 원칙 |
| **이미지·웹 검색** | 자리표시 이미지, 근거 자료 샘플 | `ImageProvider`(`app/providers/image.py`), `find_evidence` 단계만 바꾼다 | CLAUDE.md |
| **비용 습관** | 테스트는 늘 Mock | 실제 호출 테스트는 따로 돌리고, `llm_validation`(생성마다 호출 하나 더)은 필요할 때만 켠다 | CLAUDE.md "비용" |

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | 지금 상태, 다음 할 일, 작업 방식, 인수 시 교체할 계정·키 |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | 무료 배포(버셀·렌더) 절차와 한계 |
| [`docs/HARNESS-ROADMAP.md`](docs/HARNESS-ROADMAP.md) | 하네스 성능 저하 대응 로드맵(측정 → 라우팅 → 디코딩 제약 → LoRA) |
| [`docs/WBS.xlsx`](docs/WBS.xlsx) | 작업 현황(팀 공유용) |
| [`docs/planning/`](docs/planning/) | 기획서·하네스 설계서 |
| [`docs/superpowers/specs/`](docs/superpowers/specs/), [`docs/superpowers/plans/`](docs/superpowers/plans/) | 설계와 작업별 구현 계획 |
| [`design/`](design/) | 디자이너가 보낸 HTML 원본(날짜별) |
| [`CLAUDE.md`](CLAUDE.md) | 개발 규칙·구조(개발용) |

## 로컬에서 실행

필요한 것: [uv](https://docs.astral.sh/uv/)(Python 3.12), Node.js.

```bash
# 백엔드 (http://localhost:8000/docs)
cp backend/.env.example backend/.env
uv run --directory backend python -m uvicorn app.main:app --port 8000

# 프론트 (http://localhost:5173, /preview는 백엔드 없이도 열림)
npm --prefix frontend ci
npm --prefix frontend run dev

# 테스트
uv run --directory backend pytest
npm --prefix frontend test
```

## 기술 구성

- 백엔드: FastAPI, 과제별 하네스(정책 YAML·프롬프트·검증 규칙), 교체 가능한 LLM 제공자(Mock·Claude), SQLite
- 프론트엔드: React + Vite + TypeScript, 디자인 토큰, 미리보기 갤러리
- 배포: 버셀(프론트) + 렌더(백엔드), 무료 플랜
