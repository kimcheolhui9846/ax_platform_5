# 배포 가이드 (무료 구성)

이 프로토타입은 비용 0으로 띄운다. 프론트는 **버셀 무료(Hobby)**, 백엔드 API는 **렌더 무료(Free)**, AI는 **Mock**(실제 호출 없음), 데이터는 **Neon 무료 Postgres**다.

```
브라우저 ──> 버셀 (frontend, /preview 포함)
              └─ /api/* ──(vercel.json rewrites)──> 렌더 ax-coaching-api (backend, Mock)
                                                      └─ DATABASE_URL ──> Neon Postgres (세션·결과 이미지)
```

버셀이 `/api/*`를 렌더로 넘기므로 브라우저 입장에서는 같은 주소다. 그래서 백엔드에 CORS 설정이 필요 없고, 사용자 ID 헤더(`X-Client-Id`)도 그대로 간다. 프론트의 `VITE_API_BASE`는 **비워 둔다**.

> **개인 계정으로 띄운다.** 렌더·버셀·Neon·Anthropic 키는 개발자 개인 것이고, 키 값은 각 대시보드 환경 변수나 git에서 빠진 `backend/.env`에만 둔다. 인수할 때 교체·삭제할 목록은 `docs/HANDOFF.md`의 "개인 계정·키·로컬 데이터"에 있다.

## 무료 플랜의 한계 (시연 전에 알아 둘 것)

| 한계 | 영향 | 대처 |
|---|---|---|
| 렌더 Free는 15분 동안 요청이 없으면 잠든다 | 다음 첫 요청이 깨어나는 데 약 1분 걸린다. 그동안 앱 화면에 "백엔드가 연결되어 있지 않습니다"가 뜰 수 있다 | 시연 몇 분 전에 앱을 한 번 열어 깨워 둔다. 안내가 뜨면 잠시 뒤 '다시 시도' |
| 렌더 Free는 디스크가 없다 | 데이터는 렌더가 아니라 Neon Postgres에 있으므로 다시 시작해도 남는다 | 아래 "Neon(무료 Postgres) 연결"을 먼저 해 둔다. 오래 보관할 결과는 '문서 내려받기'로도 저장 |
| Neon Free는 0.5GB, 한동안 쓰지 않으면 DB가 잠든다 | 잠든 뒤 첫 요청이 몇 초 늦다(연결이 끊겨도 서버가 알아서 다시 연결한다) | 시연 몇 분 전에 앱을 한 번 열어 둔다 |
| 실제 이미지 제공자를 붙이면 이미지 바이트도 Neon에 저장된다 | Mock(SVG 자리표시)은 작지만 실제 이미지는 한 장에 수백 KB~수 MB라 0.5GB를 빨리 채울 수 있다 | 실제 이미지를 켜기 전에 Neon 사용량을 확인하고, 오래된 세션을 지우거나 파일 저장소(S3 등)로 옮긴다 |
| 렌더 Free는 월 750시간 | 한 서비스만 띄우면 한 달 내내 켜 둘 수 있는 양이다 | 서비스를 여러 개 만들지 않는다 |
| AI는 Mock | 질문·결과 글은 `[mock] …` 같은 자리표시다 | 실제 Claude 연결은 인수 기업이 정한다(아래 "나중에 바꿀 것") |

`/preview`(화면 미리보기 갤러리)는 백엔드 없이 동작하므로 이 한계와 상관없다.

## 1. 렌더에 백엔드 올리기 (한 번)

1. https://render.com 에 GitHub 계정으로 가입한다(무료, 카드 없이).
2. 대시보드에서 **New → Blueprint**를 고르고 저장소 `kimcheolhui9846/ax_platform_5`를 연결한다.
3. 렌더가 저장소 루트의 `render.yaml`을 읽어 서비스 `ax-coaching-api`(Free, Python)를 보여 준다. 그대로 **Apply**.
   - 설정은 `render.yaml`에 다 있다: 루트 폴더 `backend`, 설치 `uv sync --frozen --no-dev`, 실행 `uvicorn`, 상태 확인 `/api/v1/coaching/tasks`, 환경 변수 `PROVIDER=mock`·`STORE=postgres`·`DEBUG=false`.
   - `DATABASE_URL`은 비밀 값이라 블루프린트 화면이 값을 물어본다. 아래 "Neon 연결"에서 만든 연결 문자열을 붙여 넣는다. API 키는 넣지 않는다.
4. 첫 배포가 끝나면(몇 분) 서비스 주소를 확인한다. 보통 `https://ax-coaching-api.onrender.com`이다.
   - 브라우저로 `https://<주소>/api/v1/coaching/tasks`를 열어 과제 4개가 JSON으로 나오면 성공이다. `/docs`는 API 문서다.
5. **주소가 `ax-coaching-api.onrender.com`과 다르면**(이름이 이미 쓰여 뒤에 글자가 붙은 경우) `frontend/vercel.json`의 `rewrites` 주소를 그 주소로 고쳐 PR을 올린다.

이후 main에 머지할 때마다 렌더가 자동으로 다시 배포한다(데이터는 Neon에 있어 지워지지 않는다).

## 2. 버셀에 프론트 올리기 (한 번)

vercel.com에 GitHub 계정으로 가입하고 **Add New → Project**에서 저장소를 가져온다.

| 항목 | 값 |
|---|---|
| Import | GitHub `kimcheolhui9846/ax_platform_5` |
| Root Directory | `frontend` |
| Framework Preset | Vite (`vercel.json`이 정한다) |
| Install / Build / Output | `vercel.json`이 정한다: `npm ci` / `npm test && npm run build` / `dist` |
| Environment Variables | **없음**(`VITE_API_BASE`는 비워 둔다. `/api`는 rewrites가 렌더로 넘긴다) |

배포가 끝나면:
- `https://<프로젝트>.vercel.app/` — 앱(과제 4개가 보이면 렌더와 연결된 것)
- `https://<프로젝트>.vercel.app/preview` — 화면 미리보기 갤러리(디자이너가 html.to.design으로 가져가는 주소)
- main은 정식 주소, PR마다 미리보기 주소가 생긴다. 빌드 명령에 테스트가 있어서 테스트가 실패하면 배포되지 않는다.

## Neon(무료 Postgres) 연결 (한 번)

세션·결과 이미지를 서버 밖(Neon)에 둬서 렌더가 다시 시작해도 남게 한다. `render.yaml`은 `STORE=postgres`이고 `DATABASE_URL`이 없으면 서버가 시작하지 못한다(`STORE=postgres에는 DATABASE_URL이 필요합니다.`).

> **순서가 중요하다: 이 PR(#33)을 머지하기 전에 렌더에 `DATABASE_URL`부터 넣는다.** 안 넣고 머지하면 자동 재배포된 서버가 시작하지 못해 앱이 멈춘다.

1. https://neon.tech 에 가입한다(GitHub 로그인 가능, 카드 없이 무료).
2. **New Project**를 만든다. 이름은 자유(예: `ax-coaching`), Postgres 버전은 기본값. **리전은 렌더 서비스 리전과 가까운 곳**으로 고른다. 렌더 리전은 렌더 대시보드의 서비스 `ax-coaching-api` 화면에 나온다(예: Singapore나 Oregon이면 Neon도 Singapore나 US West).
3. 프로젝트 대시보드에서 **Connect**를 눌러 연결 문자열을 복사한다. **Direct connection**(pooled 아님)을 고르고 비밀번호가 보이게 한 뒤 복사한다. 모양: `postgresql://사용자:비밀번호@ep-….neon.tech/neondb?sslmode=require` (`sslmode=require`가 들어 있어야 한다).
4. 렌더 → `ax-coaching-api` → **Environment** → **Add Environment Variable**: Key `DATABASE_URL`, Value는 복사한 문자열 → **Save**(저장하면 렌더가 다시 배포한다).
5. 그 다음에 PR #33을 머지한다.

확인: 앱에서 과제 하나로 작업을 만든 뒤 렌더 → **Manual Deploy**(또는 Restart)를 하고, 다 뜬 다음 같은 브라우저에서 **내 작업**에 그 작업이 남아 있으면 성공이다.

비밀 값 관리:
- 연결 문자열에는 비밀번호가 들어 있다. 코드·문서·채팅에 붙이지 않는다. 렌더 Environment와 로컬 `backend/.env`(git 제외)에만 둔다.
- 로컬에서 Neon으로 해 보려면 `backend/.env`에 `STORE=postgres`와 `DATABASE_URL=…`을 넣는다. 계약 테스트를 Neon에 돌리려면 셸 환경 변수 `TEST_DATABASE_URL`에 넣는다(`backend/.env`는 읽지 않는다. 없으면 테스트는 내장 Postgres `pgserver`로 돈다). **테스트는 표를 `TRUNCATE`로 비우므로 `TEST_DATABASE_URL`은 실제 데이터와 분리된 Neon 브랜치(또는 별도 데이터베이스)를 가리켜야 한다.** `DATABASE_URL`과 같으면 테스트가 건너뛴다.
- 비밀번호가 새어 나갔으면 Neon 대시보드에서 비밀번호를 재설정하고 렌더 값을 바꾼다.

## 3. 확인 순서

1. 렌더 주소의 `/api/v1/coaching/tasks`가 JSON을 낸다(깨어나는 데 1분까지 걸릴 수 있다).
2. 버셀 주소의 홈에 과제 4개가 보인다.
3. 과제 하나로 요청 → 모드 → 질문 → 초안 만들기까지 돈다(Mock 글).
4. `/preview`가 열린다.

## 나중에 바꿀 것 (인수 기업이 정할 것, 비용 발생)

- **데이터**: 지금은 Neon 무료(0.5GB)다. 늘리거나 백업·암호화·보관 기간이 필요하면 Neon 유료나 인수 기업의 DB로 `DATABASE_URL`만 바꾼다. 세션 잠금은 서버 프로세스 하나 전제이므로 인스턴스를 늘리려면 잠금도 DB 잠금으로 바꾼다. (SQLite + 렌더 영속 디스크 구성도 가능하다: `STORE=sqlite`, `disk` 추가.)
- **실제 Claude**: 렌더 환경 변수에 `PROVIDER=claude`, `ANTHROPIC_API_KEY`(비밀 값), 필요하면 `CLAUDE_MODEL`·`CLAUDE_EFFORT`. 먼저 `scripts/claude_smoke.py`로 확인한다(`docs/HANDOFF.md` 실제 AI 연결).
- **잠들지 않게**: 유료 인스턴스는 잠들지 않는다.
