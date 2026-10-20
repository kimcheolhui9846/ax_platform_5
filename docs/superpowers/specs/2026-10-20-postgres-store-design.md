# 데이터 보존: Postgres 저장소(Neon) 설계

- 날짜: 2026-10-20
- 브랜치: `task/33-postgres-store`

## 목적

렌더 무료 서버는 디스크가 없어 다시 시작하거나(15분 무요청 뒤 잠들었다 깨기, main 머지마다 재배포) 세션·결과 이미지가 지워진다. 무료 관리형 Postgres(Neon)에 세션과 결과 이미지를 두어 시연·사용성 테스트 중에도 남게 한다. 비용 0.

## 결정 사항

- DB: Neon Postgres 무료(0.5GB, 카드 없음). 표준 Postgres라 인수 기업이 그대로 옮길 수 있다.
- 드라이버: `psycopg[binary]` 3 + `psycopg-pool`(연결 재사용, 작은 풀). Neon 풀러(pgbouncer)와도 맞도록 `prepare_threshold=None`(서버 측 준비 문 끔).
- 결과 이미지 바이트도 같은 DB(`bytea`)에 둔다. Mock 이미지는 작고, 실제 이미지가 커지면 객체 저장소로 바꾸는 것은 인수 기업 몫(`AssetStore` 계약 그대로).
- `STORE=postgres`일 때만 쓰고, 테스트 기본은 계속 `memory`. 로컬 개발 기본(`.env.example`)은 `sqlite` 그대로.
- 접속 주소 `DATABASE_URL`은 비밀 값: 렌더 대시보드 환경 변수(`render.yaml`에는 `sync: false`)와 git에서 빠진 `backend/.env`에만 둔다. 로그·오류에 찍지 않는다.

## 구조

- `app/core/postgres.py`(새): `open_pool(url) -> ConnectionPool`, `PostgresSessionStore(pool)`, `PostgresAssetStore(pool)`. 표는 시작할 때 없으면 만든다(`CREATE TABLE IF NOT EXISTS`).
  - `sessions(session_id text primary key, owner_id text not null, updated_at timestamptz not null, data jsonb not null)`, 색인 `(owner_id, updated_at desc)`.
  - 목록(`list_by_owner`·`list_all`)은 `data - 'trace'`로 무거운 trace를 빼고 읽는다(SQLite의 `json_remove`와 같은 계약).
  - `assets(asset_id text primary key, owner_id text not null, mime text not null, data bytea not null)`. `get`·`delete`는 id 형식(`asset_…`)을 먼저 본다.
- 저장소 고르기를 한 곳으로: `app/core/storage.py`(새) `build_storage(settings) -> Storage`(`sessions`, `assets`, `close()`). memory·sqlite는 지금처럼, postgres는 풀 하나를 두 저장소가 같이 쓴다. `create_app`은 이것만 부르고, 앱이 끝날 때(lifespan) `close()`로 풀을 닫는다. 기존 `build_store`·`build_asset_store`는 이 함수로 합친다.
- 설정: `StoreKind`에 `"postgres"`, `database_url: SecretStr | None`. `STORE=postgres`인데 `DATABASE_URL`이 없으면 설정을 읽을 때 실패(서버가 시작하지 않는다, 문구 `STORE=postgres에는 DATABASE_URL이 필요합니다.`).
- 평가 통계 `scripts/session_stats.py`도 같은 `build_storage`로 postgres를 읽을 수 있게 한다.

## 테스트

- 저장소 계약(`tests/test_store_contract.py`)과 파일 저장소 테스트를 Postgres에도 돌린다. Postgres는 개발 의존성 `pgserver`(내장 Postgres, Windows·Linux·macOS)로 테스트 세션마다 한 번 띄운다. `TEST_DATABASE_URL`이 있으면 그 DB를 쓴다(예: Neon 테스트 브랜치). 둘 다 안 되면 그 매개변수만 건너뛴다(건너뛴 이유를 표시).
- 테스트마다 표를 비운다(`TRUNCATE`).
- 설정: postgres + URL 없음 → 실패, postgres + URL → `build_storage`가 Postgres 저장소를 돌려줌, 풀 닫기.
- 렌더 빌드는 `--no-dev`라 `pgserver`를 깔지 않는다.

## 배포

- `render.yaml`: `STORE=postgres`, `DATABASE_URL`(`sync: false`).
- 순서(중요): 렌더 대시보드에 `DATABASE_URL`을 먼저 넣고 나서 이 PR을 머지한다. 없이 머지하면 렌더 서버가 시작하지 못한다.
- `docs/DEPLOY.md`: Neon 가입 → 프로젝트 만들기(리전은 렌더와 가까운 곳) → 연결 문자열 복사(`postgresql://…?sslmode=require`) → 렌더 환경 변수 → 확인(세션 만들고 렌더 재시작 뒤에도 남는지). 무료 한도(0.5GB, 컴퓨트 자동 일시정지 — 첫 요청이 조금 느릴 수 있다).
- `docs/HANDOFF.md`·`CLAUDE.md`: "다시 시작하면 지워진다" 문구와 저장소 설명 갱신, 인수 시 Neon 개인 계정 교체 항목 추가.

## 범위 밖

데이터 옮기기(지금 렌더의 세션은 어차피 휘발), 여러 프로세스 잠금(여전히 서버 하나 전제), 객체 저장소.
