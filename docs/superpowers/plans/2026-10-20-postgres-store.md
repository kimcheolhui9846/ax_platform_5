# Postgres 저장소(Neon) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `STORE=postgres`로 세션과 결과 이미지를 Postgres(Neon)에 남긴다.

**Architecture:** `app/core/postgres.py`에 풀과 두 저장소, `app/core/storage.py`의 `build_storage(settings)`가 저장소 종류를 한 곳에서 고른다. 계약 테스트는 내장 Postgres(`pgserver`)로 돈다.

**Tech Stack:** Python 3.12, FastAPI, psycopg 3 + psycopg-pool, pgserver(dev), pytest.

설계: `docs/superpowers/specs/2026-10-20-postgres-store-design.md` (정확한 값·문구는 설계서가 기준)

## Global Constraints

- 비밀 값 `DATABASE_URL`은 저장소(파일)에 넣지 않고 로그·오류·테스트 출력에 찍지 않는다(`SecretStr`).
- 저장소 계약은 `SessionStore`·`AssetStore` Protocol 그대로(get·save·list_by_owner·list_all·delete / put·get·delete). Postgres도 `tests/test_store_contract.py`·파일 저장소 테스트를 그대로 통과한다.
- 테스트 기본 저장소는 계속 `memory`(`tests/conftest.py`). Postgres 테스트는 개발 의존성 `pgserver` 또는 `TEST_DATABASE_URL`로만, 둘 다 없으면 건너뛴다.
- 렌더 빌드는 `uv sync --frozen --no-dev`. 운영 의존성: `psycopg[binary]`, `psycopg-pool`. 개발 의존성: `pgserver`.
- 서버는 프로세스 하나 전제(세션 잠금) 그대로.
- 코드 품질: 기능적 응집도, 자료 결합, 판단은 순수 함수, 제어 플래그 금지, 주변 스타일(한국어 docstring).
- TDD. 커밋 메시지 한국어, AI 공동저자 표기 금지. `.superpowers/` 커밋 금지.
- 명령: `uv add --directory backend …`, `uv run --directory backend pytest -q`.

---

### Task 1: Postgres 저장소와 계약 테스트

**Files:** `backend/pyproject.toml`·`backend/uv.lock`(의존성), 새 `backend/app/core/postgres.py`, `backend/tests/conftest.py`(또는 새 `tests/postgres_fixture.py`), `backend/tests/test_store_contract.py`, `backend/tests/test_assets.py`

**Interfaces — Produces:**
- `open_pool(url: str) -> psycopg_pool.ConnectionPool` (`min_size=0` 또는 1, `max_size=4`, `kwargs={"prepare_threshold": None}`, 연결 열 때 표가 없으면 만든다 — 또는 별도 `ensure_schema(pool)`)
- `PostgresSessionStore(pool)`: 계약 메서드 전부. save는 `updated_at`을 지금으로(`utcnow()`), `INSERT … ON CONFLICT (session_id) DO UPDATE`, data는 `state.model_dump_json()`을 `jsonb`로. get은 `data::text`를 `SessionState.model_validate_json`. 목록은 `data - 'trace'`, `ORDER BY updated_at DESC`.
- `PostgresAssetStore(pool)`: put(이미지 형식만, `_new_id` 재사용), get·delete(id 형식 먼저 확인).
- 테스트 픽스처: 세션 범위로 Postgres URL 하나(`TEST_DATABASE_URL` 우선, 없으면 `pgserver.get_server(tmp_dir).get_uri()`; 둘 다 실패하면 `pytest.skip("Postgres를 띄울 수 없어 건너뜀: …")`), 테스트마다 `TRUNCATE sessions, assets`.

- [ ] `uv add --directory backend "psycopg[binary]" psycopg-pool` 그리고 `uv add --directory backend --dev pgserver`.
- [ ] 계약 테스트의 `store` 픽스처 params에 `"postgres"`, 파일 저장소 테스트 픽스처에 `"postgres"`를 더한다(실패 확인: 모듈 없음).
- [ ] 구현 → `uv run --directory backend pytest -q` 통과(Postgres 매개변수가 건너뛰지 않고 실제로 도는지 출력으로 확인해 보고서에 적는다).
- [ ] 커밋 `Postgres 세션·결과 이미지 저장소와 계약 테스트`.

### Task 2: 설정과 앱 연결 (`build_storage`)

**Files:** `backend/app/core/store.py`(`StoreKind`), `backend/app/config.py`(`database_url: SecretStr | None`, postgres면 필수 검증), 새 `backend/app/core/storage.py`, `backend/app/main.py`(create_app이 `build_storage` 사용, lifespan에서 `close()`), `backend/app/core/assets.py`·`store.py`(기존 `build_asset_store`·`build_store` 정리), `scripts/session_stats.py`(같은 함수 사용), `backend/.env.example`(주석으로 postgres 예시, 값 없이), `backend/tests/test_config.py`

**Interfaces — Consumes:** Task 1. **Produces:** `Storage`(frozen dataclass: `sessions: SessionStore`, `assets: AssetStore`, `close: Callable[[], None]`), `build_storage(kind: StoreKind, database_path: Path, asset_dir: Path, database_url: str | None) -> Storage` (설정 객체 통째 대신 필요한 값만 받는다).

- [ ] 테스트 먼저: memory/sqlite가 지금과 같은 저장소를 돌려줌, postgres + URL(픽스처의 Postgres) → Postgres 저장소 둘이 같은 풀, `close()` 뒤 풀이 닫힘; `Settings(store="postgres")`에 URL이 없으면 `ValidationError`이고 메시지에 설계서 문구가 있으며 URL 값이 메시지·repr에 나오지 않음; create_app을 postgres로 띄워(픽스처 URL) 세션 하나 만들고 다시 읽기.
- [ ] 구현. create_app은 테스트가 넘기는 `store`·`assets` 인자를 지금처럼 존중한다.
- [ ] `uv run --directory backend pytest -q` → 커밋 `저장소 고르기를 build_storage 한 곳으로, STORE=postgres 설정`.

### Task 3: 배포 설정과 문서

**Files:** `render.yaml`, `docs/DEPLOY.md`, `docs/HANDOFF.md`, `CLAUDE.md`, `README.md`(데이터 휘발 언급이 있으면), `docs/WBS.xlsx`

- [ ] `render.yaml`: `STORE` 값 `postgres`, 주석 갱신(데이터는 Neon에 남는다, 렌더 자체는 여전히 디스크 없음), `- key: DATABASE_URL` + `sync: false`.
- [ ] `docs/DEPLOY.md`: 한계 표의 데이터 휘발 행 갱신, 새 절 "Neon(무료 Postgres) 연결" — 가입, 프로젝트(리전: 렌더 서비스 리전과 가까운 곳), 연결 문자열(Direct, `sslmode=require` 포함) 복사, 렌더 Environment에 `DATABASE_URL` 추가 → 저장 → 재배포, 확인 방법(세션 만들고 Manual Deploy/Restart 뒤에도 내 작업에 남는지), 무료 한도와 첫 요청 지연, **PR을 머지하기 전에 DATABASE_URL부터** 넣는 순서. 로컬에서 Neon으로 테스트하려면 `backend/.env`에 `TEST_DATABASE_URL`(값은 git 제외 파일에만). "나중에 바꿀 것"의 데이터 항목 갱신.
- [ ] `docs/HANDOFF.md`: 기준일·main(`68bf499`, PR #32까지)·테스트 수, 지금 상태 행 `| 데이터 보존(Neon Postgres) | #33 | STORE=postgres(세션·결과 이미지), 렌더가 다시 시작해도 남는다. 계약 테스트는 내장 Postgres(pgserver) |`, 다음 할 일의 데이터 보존 항목을 "Neon 가입·DATABASE_URL 입력(사용자)"로, 시연 전 확인의 "다시 시작하면 지워진다" 갱신, "개인 계정·키" 표에 Neon 행(개인 계정, 인수 시 새 프로젝트로 교체·개인 프로젝트 삭제, 연결 문자열 폐기).
- [ ] `CLAUDE.md`: 실행 절의 저장소 설명에 postgres(`DATABASE_URL`, `build_storage`), 구조의 `backend/app/core/` 줄에 `postgres.py`·`storage.py`, 배포 문단의 "다시 시작하면 데이터가 지워진다"를 Neon 기준으로.
- [ ] WBS: '데이터 보존(Neon Postgres)' 행(완료, 2026-10-20, 1, PR #33), 기준일.
- [ ] 테스트 재실행 → 커밋 `배포: Neon Postgres로 데이터 보존, 문서·WBS`.
