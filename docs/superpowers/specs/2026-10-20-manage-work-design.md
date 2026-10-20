# 작업·결과물 정리(삭제·이름 바꾸기·결과물에서 빼기) 설계

- 날짜: 2026-10-20
- 브랜치: `task/32-manage-work`

## 목적

내 작업·결과물이 쌓이기만 하고 정리할 방법이 없다. 작업을 지우고, 이름을 붙이고, 저장한 버전을 결과물 목록에서 뺄 수 있게 한다. 기능 위주(디자인은 나중에 다시 받는다).

## 결정 사항

- **작업 삭제**: 내 작업에서 작업(세션)을 통째로 지운다(질문·결과·버전·결과 이미지). 되돌릴 수 없으므로 확인 대화상자를 거친다.
- **결과물에서 빼기**: 결과물 목록에서 저장한 버전의 저장 표시만 지운다. 작업·버전은 남고 다시 저장할 수 있으므로 확인 없이 바로 빼고 알린다.
- **이름**: 작업(세션)마다 이름 하나. 비어 있으면 처음 요청 글이 이름이다. 목록(내 작업·결과물)과 내려받는 파일 이름에 쓰고 프롬프트에는 싣지 않는다.

## API (모두 owner 확인, 남의·없는 작업은 404, 세션별 잠금)

| 경로 | 본문 | 응답 | 오류 |
|---|---|---|---|
| `DELETE /sessions/{id}` | — | 204 | 404, 422(헤더) |
| `PATCH /sessions/{id}` | `{ "name": str }` 공백(줄바꿈·탭 포함)을 하나로 접고 앞뒤를 뺀 1~40자 | `SessionSummary` | 404, 422 |
| `DELETE /sessions/{id}/versions/{n}/save` | — | `SessionSummary` | 404(작업·버전), 422 |

- 이름 바꾸기와 저장 해제도 작업을 바꾼 것으로 보아 `updated_at`이 갱신된다(내 작업 목록에서 맨 위로 올라온다). 의도한 동작이다.
- 저장 해제는 이미 저장하지 않은 버전이어도 성공(멱등). 상태·`result_stale`은 건드리지 않는다.
- 삭제는 세션을 지운 뒤 그 세션의 결과 이미지(모든 버전과 지금 결과의 `ImageBlock.asset_id`)를 파일 저장소에서 지운다. 이미지 지우기는 없는 id면 조용히 넘어간다.
- 잠금: 삭제도 `_session_update`처럼 잠근 뒤 다시 읽고 지운다. 같은 세션의 다음 요청은 잠금 안에서 다시 읽어 404가 된다. 잠금 객체는 남는다(만든 세션 수를 넘지 않는다).

## 저장소 계약

- `SessionStore.delete(session_id) -> None`: 없는 id면 아무 일도 하지 않는다. 메모리·SQLite 모두(`tests/test_store_contract.py`).
- `AssetStore.delete(asset_id) -> None`: 없거나 형식이 틀린 id면 아무 일도 하지 않는다. 메모리·로컬 폴더 모두.

## 이름

- `SessionState.name: str | None = None`(옛 세션은 None).
- 순수 함수 `session_name(state) -> str`(`app/api/views.py`): `name`이 있으면 그것, 없으면 `raw_input`의 첫 줄(앞뒤 공백 제거) 40자.
- `SessionSummary.name`·`SessionView.name`(둘 다 required).
- 프론트: 내 작업 제목 `{name} · {과제 이름}`, 결과물 제목 `{name}`과 그 아래 `{과제 이름} 초안 · V{n}`.
- 파일 이름: `documentFile`의 basename을 `{안전한 이름}_V{n}`로. 안전한 이름(`lib/fileName.ts`의 순수 함수 `safeFileName`)은 `\ / : * ? " < > |`·제어문자를 빼고, 공백을 하나로, 앞뒤 공백·끝의 점을 지우고 40자. 비면 `AX_{task_type}`.

## 프론트

- `api/coaching.ts`: `deleteSession`, `renameSession`, `unsaveVersion`.
- 상태(리듀서): `sessionDeleted { seq, sessionId }` — 목록에서 빼고, 지금 들고 있는 세션이 그것이면 세션·결과·버전·근거를 비우고, 그 작업에서 이어 가던 미리보기(`carry`)도 비운다. 알림 `작업을 삭제했어요.`. `summaryChanged { seq, summary, notice }` — 목록의 그 항목을 바꾸고, 지금 세션이 그것이면 세션·결과·버전·근거를 비워(다음에 다시 받는다) 이름·저장 표시가 낡지 않게 한다.
- 알림: 이름 `작업 이름을 바꿨어요.`, 빼기 `결과물에서 뺐어요. 작업에서 다시 저장할 수 있어요.`
- handlers: `deleteSession(sessionId)`, `renameSession(sessionId, name)`, `unsaveVersion(sessionId, version)`.
- 화면:
  - `WorkScreen` 항목마다 `이름 바꾸기`·`삭제` 버튼. 각 버튼이 대화상자를 연다(`components/WorkItemDialogs`의 `RenameDialog`·`DeleteDialog`, `<dialog>` 모달). 이름 대화상자는 지금 이름을 채운 입력(최대 40자)과 `저장`·`취소`, 빈 이름이면 `저장`을 막는다. 삭제 대화상자는 `"{이름}" 작업을 삭제할까요? 질문·결과·저장한 버전이 모두 지워지고 되돌릴 수 없어요.`와 `삭제`·`취소`. 어느 대화상자든 확인을 누르면 요청을 보내고 닫는다. 닫히면 연 버튼으로 포커스를 돌린다(삭제는 항목이 사라지므로 목록 제목으로).
  - `DocumentsScreen` 항목마다 `결과물에서 빼기` 버튼.
  - 요청 중(`busy`)에는 버튼을 막는다.
- 미리보기: `work` 화면에 이름 대화상자·삭제 대화상자 프레임(`dialogFrame`).

## 테스트

- 백엔드: 저장소 계약(delete), 파일 저장소(delete), API(삭제 204 → 다시 읽기 404·목록에서 빠짐·이미지 404, 남의 작업 404, 이름 바꾸기 공백 제거·빈 이름 422·41자 422, 저장 해제 멱등·없는 버전 404), `session_name`, 계약 테스트(required).
- 프론트: `safeFileName`, 리듀서 두 액션, handlers 세 개, 목록 화면 렌더(이름·버튼), 대화상자 렌더, `documentFileOf` basename.

## 범위 밖

로그인, 공유 링크, 휴지통(삭제 취소), 여러 개 한꺼번에 지우기.
