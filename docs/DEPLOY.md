# 배포 가이드 (무료 구성)

이 프로토타입은 비용 0으로 띄운다. 프론트는 **버셀 무료(Hobby)**, 백엔드 API는 **렌더 무료(Free)**, AI는 **Mock**(실제 호출 없음)이다.

```
브라우저 ──> 버셀 (frontend, /preview 포함)
              └─ /api/* ──(vercel.json rewrites)──> 렌더 ax-coaching-api (backend, Mock)
```

버셀이 `/api/*`를 렌더로 넘기므로 브라우저 입장에서는 같은 주소다. 그래서 백엔드에 CORS 설정이 필요 없고, 사용자 ID 헤더(`X-Client-Id`)도 그대로 간다. 프론트의 `VITE_API_BASE`는 **비워 둔다**.

> **개인 계정으로 띄운다.** 렌더·버셀·Anthropic 키는 개발자 개인 것이고, 키 값은 각 대시보드 환경 변수나 git에서 빠진 `backend/.env`에만 둔다. 인수할 때 교체·삭제할 목록은 `docs/HANDOFF.md`의 "개인 계정·키·로컬 데이터"에 있다.

## 무료 플랜의 한계 (시연 전에 알아 둘 것)

| 한계 | 영향 | 대처 |
|---|---|---|
| 렌더 Free는 15분 동안 요청이 없으면 잠든다 | 다음 첫 요청이 깨어나는 데 약 1분 걸린다. 그동안 앱 화면에 "백엔드가 연결되어 있지 않습니다"가 뜰 수 있다 | 시연 몇 분 전에 앱을 한 번 열어 깨워 둔다. 안내가 뜨면 잠시 뒤 '다시 시도' |
| 렌더 Free는 디스크가 없다 | 서버가 다시 시작하면(잠들었다 깸·재배포) 세션·결과·이미지가 모두 지워진다 | 시연 중에는 남는다. 오래 보관할 결과는 '문서 내려받기'로 저장 |
| 렌더 Free는 월 750시간 | 한 서비스만 띄우면 한 달 내내 켜 둘 수 있는 양이다 | 서비스를 여러 개 만들지 않는다 |
| AI는 Mock | 질문·결과 글은 `[mock] …` 같은 자리표시다 | 실제 Claude 연결은 인수 기업이 정한다(아래 "나중에 바꿀 것") |

`/preview`(화면 미리보기 갤러리)는 백엔드 없이 동작하므로 이 한계와 상관없다.

## 1. 렌더에 백엔드 올리기 (한 번)

1. https://render.com 에 GitHub 계정으로 가입한다(무료, 카드 없이).
2. 대시보드에서 **New → Blueprint**를 고르고 저장소 `kimcheolhui9846/ax_platform_5`를 연결한다.
3. 렌더가 저장소 루트의 `render.yaml`을 읽어 서비스 `ax-coaching-api`(Free, Python)를 보여 준다. 그대로 **Apply**.
   - 설정은 `render.yaml`에 다 있다: 루트 폴더 `backend`, 설치 `uv sync --frozen --no-dev`, 실행 `uvicorn`, 상태 확인 `/api/v1/coaching/tasks`, 환경 변수 `PROVIDER=mock`·`STORE=sqlite`·`DEBUG=false`.
   - 비밀 값(API 키)은 넣지 않는다.
4. 첫 배포가 끝나면(몇 분) 서비스 주소를 확인한다. 보통 `https://ax-coaching-api.onrender.com`이다.
   - 브라우저로 `https://<주소>/api/v1/coaching/tasks`를 열어 과제 4개가 JSON으로 나오면 성공이다. `/docs`는 API 문서다.
5. **주소가 `ax-coaching-api.onrender.com`과 다르면**(이름이 이미 쓰여 뒤에 글자가 붙은 경우) `frontend/vercel.json`의 `rewrites` 주소를 그 주소로 고쳐 PR을 올린다.

이후 main에 머지할 때마다 렌더가 자동으로 다시 배포한다(이때 데이터는 지워진다).

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

## 3. 확인 순서

1. 렌더 주소의 `/api/v1/coaching/tasks`가 JSON을 낸다(깨어나는 데 1분까지 걸릴 수 있다).
2. 버셀 주소의 홈에 과제 4개가 보인다.
3. 과제 하나로 요청 → 모드 → 질문 → 초안 만들기까지 돈다(Mock 글).
4. `/preview`가 열린다.

## 나중에 바꿀 것 (인수 기업이 정할 것, 비용 발생)

- **데이터를 남기려면**: 렌더 유료 인스턴스 + 영속 디스크. `render.yaml`의 `plan`을 유료로, `disk`(예: `mountPath: /opt/render/project/src/backend/data`, `sizeGB: 1`)를 더하면 기본 경로(`backend/data/sessions.db`, `backend/data/assets`)가 그대로 디스크에 남는다. 디스크를 붙이면 인스턴스는 하나만 쓸 수 있는데, 이 서버는 원래 프로세스 하나 전제다(세션 잠금). 또는 저장소를 관리형 DB로 바꾼다(`SessionStore` 계약, `tests/test_store_contract.py`).
- **실제 Claude**: 렌더 환경 변수에 `PROVIDER=claude`, `ANTHROPIC_API_KEY`(비밀 값), 필요하면 `CLAUDE_MODEL`·`CLAUDE_EFFORT`. 먼저 `scripts/claude_smoke.py`로 확인한다(`docs/HANDOFF.md` 실제 AI 연결).
- **잠들지 않게**: 유료 인스턴스는 잠들지 않는다.
