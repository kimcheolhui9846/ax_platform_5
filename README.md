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

## 남은 일 — 팀에서 상의할 것

| 할 일 | 맡을 사람 | 지금 상태 | 상의할 점 |
|---|---|---|---|
| **디자인 검수** — 모바일 390px 화면 확인, `/preview`를 html.to.design으로 피그마에 가져와 다듬기 | 디자이너 | 미리보기 주소 준비됨 | 고칠 화면과 우선순위. 수정본(HTML)을 주면 개발이 바뀐 화면만 반영한다([`design/README.md`](design/README.md)) |
| **AI 품질 튜닝** — 과제별 질문 순서·준비도 기준·프롬프트 다듬기 | 인수 기업 | Mock으로 흐름만 완성 | 실제 모델 호출 비용이 든다. 어떤 모델·노력 수준을 쓸지, 평가 시나리오(`evals/`)로 무엇을 잴지 |
| **실제 AI 호출** — Mock 대신 Claude | 인수 기업 | 어댑터 준비 완료(`PROVIDER=claude` + API 키) | 사용할 모델과 월 예산. 확인 스크립트 `scripts/claude_smoke.py` |
| **결과 이미지 생성** — 지금은 회색 자리표시 이미지 | 인수 기업 | 연결 자리(`ImageProvider`)만 있음 | 이미지 생성 서비스 선택과 비용 |
| **근거 자료 웹 검색** — 지금은 상품기획 샘플 2건 | 인수 기업 | 바꿀 자리(`find_evidence`)만 있음 | 웹 검색 서비스 선택, 출처 표시·검증 방식 |
| **데이터 보관** — 지금은 재시작하면 지워짐 | 인수 기업 | 무료 플랜 | 유료 서버·디스크 또는 DB 전환([`docs/DEPLOY.md`](docs/DEPLOY.md) "나중에 바꿀 것") |
| **평가·발표** | 팀 | 예정 | 기획서 14장 지표 중 무엇을 보여 줄지, 시연 시나리오 |

진행 현황은 [`docs/WBS.xlsx`](docs/WBS.xlsx)에 있고, PR을 머지할 때마다 갱신합니다.

## 문서

| 문서 | 내용 |
|---|---|
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | 지금 상태, 다음 할 일, 작업 방식, 인수 시 교체할 계정·키 |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | 무료 배포(버셀·렌더) 절차와 한계 |
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
