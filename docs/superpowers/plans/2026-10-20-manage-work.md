# 작업·결과물 정리 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 작업 삭제, 작업 이름 바꾸기, 결과물에서 빼기(저장 해제)를 백엔드 API와 화면에 더한다.

**Architecture:** 저장소 계약에 `delete`를 더하고(세션·파일), 라우터는 기존 `_session_update` 잠금 패턴으로 세 경로를 낸다. 이름은 `SessionState.name`과 순수 함수 `session_name`. 프론트는 `api/coaching.ts` → handlers(요청) → 리듀서 두 액션 → 목록 화면의 버튼·대화상자.

**Tech Stack:** FastAPI·Pydantic·pytest(backend), React 19·TS·vitest renderToString(frontend), openapi-typescript.

설계: `docs/superpowers/specs/2026-10-20-manage-work-design.md` (정확한 값·문구는 설계서가 기준)

## Global Constraints

- 오류 본문은 `{"detail": 한국어}`, 문구는 `app/core/messages.py`에 모은다. OpenAPI에는 경로마다 낼 수 있는 오류만 `error_responses(...)`.
- 응답 모델은 `ContractModel`을 상속하고 모든 속성이 required(`tests/test_contract.py`).
- 남의 세션 = 없는 세션 = 404. 세션을 바꾸는 요청은 세션별 잠금.
- 이름: 앞뒤 공백 제거 후 1~40자. 비면 처음 요청 글 첫 줄 40자. 프롬프트에는 싣지 않는다.
- 알림 문구: `작업을 삭제했어요.` / `작업 이름을 바꿨어요.` / `결과물에서 뺐어요. 작업에서 다시 저장할 수 있어요.`
- 삭제 확인 문구: `"{이름}" 작업을 삭제할까요? 질문·결과·저장한 버전이 모두 지워지고 되돌릴 수 없어요.`
- 프론트: 상태는 리듀서만 바꾼다. 컴포넌트는 props만(대화상자 열림 같은 부품 안 UI 상태만 가진다). 백엔드 호출은 `api/coaching.ts`만. CSS 색·글자 크기·폭·선·모서리는 `var(--…)`.
- TDD. 커밋 메시지는 한국어, AI 공동저자 표기 금지. `.superpowers/`는 커밋하지 않는다.
- 명령(저장소 루트): `uv run --directory backend pytest -q`, `npm --prefix frontend run gen:api`, `npm --prefix frontend test`, `npm --prefix frontend run build`.

---

### Task 1: 저장소 계약에 delete (세션·파일)

**Files:** `backend/app/core/store.py`, `backend/app/core/assets.py`, `backend/tests/test_store_contract.py`, `backend/tests/test_assets.py`

**Interfaces — Produces:** `SessionStore.delete(self, session_id: str) -> None`, `AssetStore.delete(self, asset_id: str) -> None` (Protocol + 모든 구현)

- [ ] 계약 테스트 먼저(두 구현에 같이 도는 픽스처에): 저장 → delete → `get`이 None·`list_by_owner`·`list_all`에서 빠짐. 없는 id delete는 예외 없음. 다른 세션은 그대로.
- [ ] 파일 저장소 테스트(메모리·로컬 둘 다; `test_assets.py`의 기존 픽스처 방식을 따른다): put → delete → get None. 없는 id·형식이 틀린 id(`../x`) delete는 예외 없음(로컬은 폴더 밖을 건드리지 않는다).
- [ ] 실패 확인 → 구현: 메모리 `pop`, SQLite `DELETE FROM sessions WHERE session_id = ?`, 로컬 파일은 `_ASSET_ID` 형식 검사 후 `.json`을 먼저 지우고 `.bin`(missing_ok). Protocol docstring에 계약 한 줄씩.
- [ ] `uv run --directory backend pytest -q` 통과 → 커밋 `저장소 계약에 삭제(세션·결과 이미지)`.

### Task 2: 백엔드 API (이름·삭제·저장 해제)

**Files:** `backend/app/core/state.py`(SessionState.name), `backend/app/harness/base.py`(`unsave_version`), `backend/app/schemas/coaching.py`(`RenameSessionRequest`, `SessionSummary.name`, `SessionView.name`), `backend/app/api/views.py`(`session_name`, 요약·뷰에 name), `backend/app/api/coaching.py`(세 경로), `backend/app/api/locks.py`(docstring), `backend/app/core/messages.py`(필요하면), 새 테스트 `backend/tests/test_api_manage.py`, `backend/tests/test_api_views.py`

**Interfaces — Consumes:** Task 1의 `delete`. **Produces:**
- `SessionState.name: str | None = None`
- `BaseHarness.unsave_version(state, number) -> ResultVersion | None` (없는 번호 None, 있으면 `saved=False`)
- `session_name(state: SessionState) -> str` (순수)
- `session_asset_ids(state: SessionState) -> set[str]` (순수, `app/core/results.py` 또는 views가 아닌 core 쪽에 둔다: 모든 버전 결과 + 지금 결과의 섹션 블록 중 `ImageBlock.asset_id`)
- 경로: `DELETE /api/v1/coaching/sessions/{session_id}` → 204(`status_code=204`, `response_class=Response`), `PATCH /api/v1/coaching/sessions/{session_id}` body `RenameSessionRequest` → `SessionSummary`, `DELETE /api/v1/coaching/sessions/{session_id}/versions/{version}/save` → `SessionSummary`
- `RenameSessionRequest.name`: 앞뒤 공백 제거 후 1~40자(Pydantic `field_validator`로 strip 후 `StringConstraints`/길이 검사; 실패는 422)

- [ ] 테스트 먼저 (`tests/conftest.py`의 `api_client(app, client_id=...)` 사용, 기존 `test_api_versions.py` 흐름을 본보기로 세션 만들기·생성·저장):
  - 삭제: 204 → `GET /sessions/{id}` 404, `GET /sessions` 목록에서 빠짐, 결과 이미지가 있던 과제(브랜딩: 정책 `image_generation`이 켜져 있으면; 아니면 assets에 직접 put한 id를 버전에 넣은 상태로)면 `GET /assets/{id}` 404. 남의 작업 삭제 404(그리고 주인 것은 남음). 없는 id 404.
  - 이름: `"  새 이름  "` → 응답 `name == "새 이름"`, 목록·`GET /sessions/{id}`의 name도. `"   "` 422, 41자 422, 40자 OK. 남의 작업 404.
  - 저장 해제: 저장 → 해제 → 응답 `saved_versions == []`, 다시 해제 200(멱등), 없는 버전 404, 남의 작업 404.
  - `session_name`: name 있으면 그것, 없으면 raw_input 첫 줄 strip 40자(여러 줄·긴 글 케이스).
  - `session_asset_ids`: 이미지 블록이 있는 버전 둘 → 두 id.
- [ ] 실패 확인 → 구현. 삭제 라우트:
```python
@router.delete("/sessions/{session_id}", status_code=204, response_class=Response, responses=error_responses(404, 422))
def delete_session(session_id: str, registry: Registry, store: Store, assets: Assets, locks: Locks, owner: Owner) -> Response:
    """작업을 통째로 지운다(결과 이미지 포함). 되돌릴 수 없다."""
    _load(registry, store, session_id, owner)
    with locks.hold(session_id):
        state, _ = _load(registry, store, session_id, owner)
        store.delete(session_id)
    for asset_id in session_asset_ids(state):
        assets.delete(asset_id)
    return Response(status_code=204)
```
  이름·저장 해제는 `_session_update` 안에서 바꾸고 `to_session_summary(state, harness.policy.title)`를 돌려준다(저장은 블록이 끝난 뒤라 `updated_at`이 바뀐 요약을 내려면 블록 밖에서 만든다). `_session_update` docstring의 "세션은 지우지 않으므로…" 문장을 "잠근 뒤 다시 읽으므로 그사이 지워졌으면 404"로 고친다. `locks.py` docstring도 "만든 세션 수만큼"으로.
- [ ] `to_session_summary`·`to_session_view`에 `name=session_name(state)`.
- [ ] `uv run --directory backend pytest -q` 통과(test_contract 포함) → 커밋 `작업 삭제·이름 바꾸기·결과물에서 빼기 API`.

### Task 3: 프론트 데이터 흐름 (API·상태·handlers·파일 이름)

**Files:** `frontend/openapi.json`·`frontend/src/api/schema.d.ts`(생성), `frontend/src/api/coaching.ts`, `frontend/src/app/state.ts`(+test), `frontend/src/app/handlers.ts`(+test), `frontend/src/app/view.tsx`(Handlers 타입), `frontend/src/preview/handlers.ts`, 새 `frontend/src/lib/fileName.ts`(+test), `frontend/src/app/documentFile.ts`(+test), `frontend/src/testing/factories.ts`·`frontend/src/preview/fixtures.ts`(name 필드)

**Interfaces — Produces:**
- `deleteSession(sessionId): Promise<ApiResult<void>>`(204), `renameSession(sessionId, name): Promise<ApiResult<SessionSummary>>`, `unsaveVersion(sessionId, version): Promise<ApiResult<SessionSummary>>`
- Action `{ type: "sessionDeleted"; seq: number; sessionId: string }`, `{ type: "summaryChanged"; seq: number; summary: SessionSummary; notice: string }` (seq 응답이라 `Settled` 처리 경로를 따른다: 지금 기다리는 요청 번호일 때만)
- 알림 상수(handlers.ts): `SESSION_DELETED_NOTICE`, `SESSION_RENAMED_NOTICE`, `VERSION_UNSAVED_NOTICE` (Global Constraints 문구)
- Handlers: `deleteSession(sessionId: string)`, `renameSession(sessionId: string, name: string)`, `unsaveVersion(sessionId: string, version: number)`
- `safeFileName(name: string, fallback: string): string` (설계서 규칙), documentFile basename `${safeFileName(session.name, `AX_${task_type}`)}_V${n}`

- [ ] `npm --prefix frontend run gen:api`(백엔드 Task 2가 끝난 상태) → 타입 오류를 따라 픽스처에 `name` 추가.
- [ ] 테스트 먼저: 리듀서(삭제: 목록에서 빠지고 지금 세션이면 session·result·version·evidence null, 알림 `작업을 삭제했어요.`, 다른 seq면 무시; 바뀜: 목록 항목 교체·알림·지금 세션이면 session·result·version null), handlers(각각 맞는 요청 함수와 done 액션 — 기존 handlers 테스트처럼 `calls[0].request()`를 부르고 `vi.mock("../api/coaching")` 패턴을 따른다), `safeFileName`(금지 문자·제어문자·공백 접기·끝 점·40자·빈 값 fallback), documentFile basename(이름 있음/없음).
- [ ] 실패 확인 → 구현 → `npm --prefix frontend test`, `npm --prefix frontend run build` 통과 → 커밋 `작업 정리 요청·상태, 이름으로 파일 이름`.

### Task 4: 목록 화면 버튼·대화상자, 미리보기

**Files:** `frontend/src/screens/WorkScreen.tsx`, `frontend/src/screens/DocumentsScreen.tsx`, 새 `frontend/src/components/WorkItemDialogs.tsx`, `frontend/src/app/view.tsx`(props 연결, busy), `frontend/src/components/components.test.tsx`·`frontend/src/app/view.test.tsx`, `frontend/src/preview/frames.tsx`·`frames.test.tsx`, `frontend/src/styles/screens.css`(필요하면, 토큰만)

**Interfaces — Consumes:** Task 3 Handlers. **Produces:** `RenameForm({ titleId, name, busy, onSave(name), onCancel })`·`DeleteConfirm({ titleId, name, busy, onDelete, onCancel })`(대화상자 안 양식 — 갤러리 `dialogFrame`이 그대로 그린다), `WorkItemActions({ summary, busy, onRename, onDelete })`(버튼 두 개와 `<dialog>` 모달, 열림 상태만 가진다; `SupplementPanel`의 showModal/close·포커스 복귀 패턴을 따른다)

- [ ] 테스트 먼저(renderToString): 내 작업 항목에 이름·`이름 바꾸기`·`삭제`, busy면 막힘; 결과물 항목에 이름·`{과제} 초안 · V{n}`·`결과물에서 빼기`; `RenameForm`은 지금 이름이 채워지고 maxLength 40, 빈 이름이면 저장 막힘(입력값 판단은 순수 함수 `canRename(text)`로 빼서 테스트); `DeleteConfirm`은 설계서 확인 문구.
- [ ] 구현: `WorkScreen` props에 `busy`, `onRename(sessionId, name)`, `onDelete(sessionId)`. `DocumentsScreen` props에 `busy`, `onUnsave(sessionId, version)`. view.tsx에서 handlers 연결.
- [ ] 미리보기: `work` 다음에 `work-rename`·`work-delete` 프레임(`dialogFrame`으로 `RenameForm`·`DeleteConfirm`을 그린다), frames.test 목록 갱신.
- [ ] `npm --prefix frontend test`, `npm --prefix frontend run build` 통과 → 커밋 `내 작업·결과물에 삭제·이름 바꾸기·빼기 버튼과 대화상자`.

### Task 5: 문서·WBS·HANDOFF

- [ ] `CLAUDE.md`: `backend/app/core/` 줄의 저장소 설명에 `delete`(세션·파일) 계약, "API 계약/구조"에 `app/api` 라우터 설명은 그대로, 하네스 원칙 끝에 "작업 삭제(`DELETE /sessions/{id}`, 결과 이미지까지)·이름(`PATCH /sessions/{id}`, `session_name`, 프롬프트에 싣지 않음)·결과물에서 빼기(`DELETE …/versions/{n}/save`, 멱등)" 한 줄. 프론트 `app/` 설명에 `sessionDeleted`·`summaryChanged`, `lib/` 설명에 `fileName`(`safeFileName`).
- [ ] WBS: 4.x에 '작업·결과물 정리(삭제·이름·빼기)' 행 추가(완료, 2026-10-20, 1, PR #32), 기준일. 그리고 후순위 항목 두 개를 '예정'으로 추가: '로그인(다른 기기에서 내 작업)', '결과물 공유 링크(읽기 전용)'.
- [ ] HANDOFF: 기준일, main(`ade3b08`, PR #31까지), 테스트 수(실행 결과), 지금 상태 행(#32), 다음 할 일에 "데이터 보존(Neon Postgres, 다음 PR)"과 "후순위: 로그인·공유 링크".
- [ ] 테스트·빌드 확인 → 커밋 `문서: 작업 정리, WBS·HANDOFF`.
