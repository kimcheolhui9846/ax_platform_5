"""코칭 API. 설계서 10.1 엔드포인트 + 이전 답변 수정 + 세션 조회 + 디버그 trace."""
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.deps import Assets, Locks, Owner, Registry, Store, require_debug
from app.api.locks import SessionLocks
from app.api.responses import error_responses
from app.api.views import (
    to_evidence_items,
    to_result_view,
    to_session_context,
    to_session_summary,
    to_session_view,
    to_task_form,
    to_task_summary,
    to_version_view,
)
from app.core.messages import (
    EVIDENCE_NOT_FOUND_MESSAGE,
    NOTICE_REQUIRED_MESSAGE,
    PREVIOUS_SESSION_NOT_FOUND_MESSAGE,
    RESULT_NOT_READY_MESSAGE,
    SECTION_NOT_FOUND_MESSAGE,
    SESSION_NOT_FOUND_MESSAGE,
    VERSION_NOT_FOUND_MESSAGE,
    unknown_task_message,
)
from app.core.results import utcnow
from app.core.state import Answer, CarriedContext, SessionState, TraceEntry, session_asset_ids
from app.core.store import SessionStore
from app.harness.base import BaseHarness, find_version
from app.harness.carry import build_context
from app.harness.errors import GenerationFailed, HarnessError, UnknownTaskError
from app.harness.policy import TaskPolicy
from app.providers.base import ProviderError
from app.schemas.coaching import (
    AnswerRequest,
    CreateSessionRequest,
    EditSectionRequest,
    EvidenceItem,
    RenameSessionRequest,
    ResultView,
    ReviseAnswerRequest,
    SessionContext,
    SessionSummary,
    SessionView,
    SupplementsRequest,
    TaskForm,
    TaskSummary,
    VersionView,
)

# 오류 본문은 app/api/errors.py가 모두 ErrorBody 모양으로 만든다. 경로마다 낼 수 있는 오류만 선언하고
# 500은 어디서나 날 수 있어 라우터 공통으로 둔다.
router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"], responses=error_responses(500))


def _harness(registry: Registry, task_type: str) -> BaseHarness:
    try:
        return registry.get(task_type)
    except UnknownTaskError:
        raise HTTPException(status_code=404, detail=unknown_task_message(task_type)) from None


def _load(
    registry: Registry, store: Store, session_id: str, owner: str
) -> tuple[SessionState, BaseHarness]:
    """남의 세션은 없는 세션과 같은 404다(있는지조차 알리지 않는다)."""
    state = store.get(session_id)
    if state is None or state.owner_id != owner:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    return state, _harness(registry, state.task_type)


def _carried(
    registry: Registry, store: Store, owner: str, target: TaskPolicy, session_id: str, version: int | None
) -> CarriedContext:
    """이어 갈 이전 작업의 그 버전(없으면 마지막)으로 가져올 기준을 만든다. 남의·없는 작업, 결과·버전이 없으면 404."""
    source = store.get(session_id)
    if source is None or source.owner_id != owner or source.task_type not in registry:
        raise HTTPException(status_code=404, detail=PREVIOUS_SESSION_NOT_FOUND_MESSAGE)
    if not source.versions:
        raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
    found = source.versions[-1] if version is None else find_version(source.versions, version)
    if found is None:
        raise HTTPException(status_code=404, detail=VERSION_NOT_FOUND_MESSAGE)
    source_harness = registry.get(source.task_type)
    return build_context(source, found, source_harness.policy.title, target, source_harness.private(source))


@contextmanager
def _session_update(
    locks: SessionLocks, registry: Registry, store: SessionStore, session_id: str, owner: str
) -> Iterator[tuple[SessionState, BaseHarness]]:
    """세션을 잠그고 읽어 블록에 넘긴 뒤 저장한다. 같은 세션을 바꾸는 요청은 한 번에 하나씩 돈다.

    AI 호출·생성 실패(502)나 입력·규칙 문제(HarnessError, 422)로 끝나도 그때의 state를 저장하고 오류를 다시
    던진다. 하네스는 이런 실패에서 state를 시작 때로 되돌리고 trace(성공한 LLM 호출 기록 포함)와 FAILED 표시만
    남기므로, 저장해도 바뀌는 것은 그 기록뿐이다. 응답 문구는 app/api/errors.py의 예외 처리기가 정한다.

    잠금은 있는(그리고 내) 세션에만 만든다. 없는 id는 잠그기 전에 404로 끝낸다. 잠근 뒤 다시 읽으므로 앞선 요청이
    저장한 최신 상태로 일하고, 그사이 지워졌으면 404다.
    """
    _load(registry, store, session_id, owner)
    with locks.hold(session_id):
        state, harness = _load(registry, store, session_id, owner)
        try:
            yield state, harness
        except (ProviderError, GenerationFailed, HarnessError):
            store.save(state)
            raise
        store.save(state)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(registry: Registry) -> list[TaskSummary]:
    return [to_task_summary(h.policy, len(h.evidence)) for h in registry.all()]


@router.get("/tasks/{task_type}/form", response_model=TaskForm, responses=error_responses(404))
def get_task_form(task_type: str, registry: Registry) -> TaskForm:
    return to_task_form(_harness(registry, task_type).policy)


@router.get("/tasks/{task_type}/context", response_model=SessionContext, responses=error_responses(404, 422))
def preview_context(
    task_type: str,
    session_id: str,
    registry: Registry,
    store: Store,
    owner: Owner,
    version: Annotated[int | None, Query(ge=1)] = None,
) -> SessionContext:
    """다음 과제로 이어가기 미리보기: 이 과제에 가져올 이전 작업의 기준(세션을 만들 때와 같은 판단)."""
    harness = _harness(registry, task_type)
    context = _carried(registry, store, owner, harness.policy, session_id, version)
    return to_session_context(context, harness.policy.labels)


@router.post(
    "/tasks/{task_type}/sessions",
    response_model=SessionView,
    status_code=201,
    responses=error_responses(404, 422, 502, 503),
)
def create_session(
    task_type: str, body: CreateSessionRequest, registry: Registry, store: Store, owner: Owner
) -> SessionView:
    # 없는 과제·남의 이전 작업은 404가 먼저다(동의 여부보다 앞선다)
    harness = _harness(registry, task_type)
    context = (
        _carried(registry, store, owner, harness.policy, body.from_session_id, body.from_version)
        if body.from_session_id is not None
        else None
    )
    if not body.notice_acknowledged:
        raise HTTPException(422, NOTICE_REQUIRED_MESSAGE)
    state = harness.start(body.raw_input, body.mode, owner_id=owner, context=context, notice_acknowledged_at=utcnow())
    store.save(state)
    return to_session_view(state, harness)


@router.get("/sessions", response_model=list[SessionSummary], responses=error_responses(422))
def list_sessions(registry: Registry, store: Store, owner: Owner) -> list[SessionSummary]:
    """내 세션 요약(최근에 바뀐 순서). 등록부에서 빠진 과제의 세션은 건너뛴다."""
    return [
        to_session_summary(state, registry.get(state.task_type).policy.title)
        for state in store.list_by_owner(owner)
        if state.task_type in registry
    ]


@router.delete("/sessions/{session_id}", status_code=204, response_class=Response, responses=error_responses(404, 422))
def delete_session(
    session_id: str, registry: Registry, store: Store, assets: Assets, locks: Locks, owner: Owner
) -> Response:
    """작업을 통째로 지운다(결과 이미지 파일 포함). 되돌릴 수 없다."""
    _load(registry, store, session_id, owner)
    with locks.hold(session_id):
        state, _ = _load(registry, store, session_id, owner)
        store.delete(session_id)
    for asset_id in session_asset_ids(state):
        assets.delete(asset_id)
    return Response(status_code=204)


@router.patch("/sessions/{session_id}", response_model=SessionSummary, responses=error_responses(404, 422))
def rename_session(
    session_id: str, body: RenameSessionRequest, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionSummary:
    """작업 이름을 바꾼다(앞뒤 공백 제거 후 1~40자). 프롬프트에는 싣지 않는다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        state.name = body.name
    return to_session_summary(state, harness.policy.title)


@router.delete(
    "/sessions/{session_id}/versions/{version}/save",
    response_model=SessionSummary,
    responses=error_responses(404, 422),
)
def unsave_version(
    session_id: str, version: int, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionSummary:
    """그 버전의 저장 표시를 지운다(결과물 목록에서 빠진다). 저장하지 않았어도 그대로 성공한다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        if harness.unsave_version(state, version) is None:
            raise HTTPException(status_code=404, detail=VERSION_NOT_FOUND_MESSAGE)
    return to_session_summary(state, harness.policy.title)


@router.delete("/sessions/{session_id}/context", response_model=SessionView, responses=error_responses(404, 422, 502, 503))
def clear_context(session_id: str, registry: Registry, store: Store, locks: Locks, owner: Owner) -> SessionView:
    """이전 과제에서 가져온 내용을 뺀다. 가져온 내용이 없으면 그대로다. 뺀 필드는 다시 물을 수 있다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.clear_context(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}", response_model=SessionView, responses=error_responses(404, 422))
def get_session(session_id: str, registry: Registry, store: Store, owner: Owner) -> SessionView:
    state, harness = _load(registry, store, session_id, owner)
    return to_session_view(state, harness)


@router.post(
    "/sessions/{session_id}/answers", response_model=SessionView, responses=error_responses(404, 422, 502, 503)
)
def submit_answer(
    session_id: str, body: AnswerRequest, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionView:
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.apply_answer(state, Answer(**body.model_dump(exclude={"private"})), private=body.private)
    return to_session_view(state, harness)


@router.patch(
    "/sessions/{session_id}/answers/{question_id}",
    response_model=SessionView,
    responses=error_responses(404, 422, 502, 503),
)
def revise_answer(
    session_id: str,
    question_id: str,
    body: ReviseAnswerRequest,
    registry: Registry,
    store: Store,
    locks: Locks,
    owner: Owner,
) -> SessionView:
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.revise_answer(
            state, Answer(question_id=question_id, **body.model_dump(exclude={"private"})), private=body.private
        )
    return to_session_view(state, harness)


@router.post(
    "/sessions/{session_id}/generate", response_model=ResultView, responses=error_responses(404, 422, 502, 503)
)
def generate(session_id: str, registry: Registry, store: Store, locks: Locks, owner: Owner) -> ResultView:
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.generate(state)
    return to_result_view(state, harness.policy.fields, harness.policy.supplement_fields)


@router.post(
    "/sessions/{session_id}/continue", response_model=SessionView, responses=error_responses(404, 422, 502, 503)
)
def continue_session(
    session_id: str, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionView:
    """결과를 만든 뒤 질문을 이어 간다. 남은 질문이 없으면 세션은 그대로다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.resume(state)
    return to_session_view(state, harness)


@router.put("/sessions/{session_id}/supplements", response_model=SessionView, responses=error_responses(404, 422))
def save_supplements(
    session_id: str, body: SupplementsRequest, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionView:
    """미확인 정보를 저장한다(사용자 입력·검증 전). 초안에 반영은 다시 생성(generate)이다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.set_supplements(state, body.values, private=body.private)
    return to_session_view(state, harness)


@router.post(
    "/sessions/{session_id}/question/original",
    response_model=SessionView,
    responses=error_responses(404, 422),
)
def show_original_question(
    session_id: str, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> SessionView:
    """'원래 예시 보기'. 사다리 질문을 기본 질문으로 되돌린다(LLM 호출 없음)."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        harness.show_original(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}/result", response_model=ResultView, responses=error_responses(404, 422))
def get_result(session_id: str, registry: Registry, store: Store, owner: Owner) -> ResultView:
    state, harness = _load(registry, store, session_id, owner)
    if state.result is None:
        raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
    return to_result_view(state, harness.policy.fields, harness.policy.supplement_fields)


@router.get(
    "/sessions/{session_id}/versions/{version}",
    response_model=VersionView,
    responses=error_responses(404, 422),
)
def get_version(session_id: str, version: int, registry: Registry, store: Store, owner: Owner) -> VersionView:
    state, harness = _load(registry, store, session_id, owner)
    found = find_version(state.versions, version)
    if found is None:
        raise HTTPException(status_code=404, detail=VERSION_NOT_FOUND_MESSAGE)
    return to_version_view(state, found, harness.policy.fields, harness.policy.supplement_fields)


@router.post(
    "/sessions/{session_id}/versions/{version}/save",
    response_model=VersionView,
    responses=error_responses(404, 422),
)
def save_version(
    session_id: str, version: int, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> VersionView:
    """그 버전에 저장 표시를 한다(결과물 목록에 모인다). 이미 저장했어도 그대로 성공한다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        saved = harness.save_version(state, version)
        if saved is None:
            raise HTTPException(status_code=404, detail=VERSION_NOT_FOUND_MESSAGE)
    return to_version_view(state, saved, harness.policy.fields, harness.policy.supplement_fields)


@router.patch(
    "/sessions/{session_id}/result/sections/{order}",
    response_model=ResultView,
    responses=error_responses(404, 422),
)
def edit_result_section(
    session_id: str, order: int, body: EditSectionRequest, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> ResultView:
    """결과 섹션 하나의 문구를 고친 새 버전(edit). LLM을 부르지 않는다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        if state.result is None:
            raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
        if not harness.edit_section(state, order, body.text):
            raise HTTPException(status_code=404, detail=SECTION_NOT_FOUND_MESSAGE)
    return to_result_view(state, harness.policy.fields, harness.policy.supplement_fields)


@router.get(
    "/sessions/{session_id}/evidence",
    response_model=list[EvidenceItem],
    responses=error_responses(404, 422),
)
def list_evidence(session_id: str, registry: Registry, store: Store, owner: Owner) -> list[EvidenceItem]:
    """결과를 검토할 근거 자료(지금은 샘플). 결과가 있어야 검토할 수 있다."""
    state, harness = _load(registry, store, session_id, owner)
    if state.result is None:
        raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
    return to_evidence_items(harness.find_evidence(state))


@router.post(
    "/sessions/{session_id}/evidence/{source_id}/apply",
    response_model=ResultView,
    responses=error_responses(404, 422),
)
def apply_evidence(
    session_id: str, source_id: str, registry: Registry, store: Store, locks: Locks, owner: Owner
) -> ResultView:
    """근거 자료의 점검 문구와 출처를 결과에 붙인 새 버전(evidence). LLM을 부르지 않는다."""
    with _session_update(locks, registry, store, session_id, owner) as (state, harness):
        if state.result is None:
            raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
        if not harness.apply_evidence(state, source_id):
            raise HTTPException(status_code=404, detail=EVIDENCE_NOT_FOUND_MESSAGE)
    return to_result_view(state, harness.policy.fields, harness.policy.supplement_fields)


@router.get(
    "/sessions/{session_id}/trace",
    response_model=list[TraceEntry],
    responses=error_responses(404, 422),
    dependencies=[Depends(require_debug)],
)
def get_trace(session_id: str, registry: Registry, store: Store, owner: Owner) -> list[TraceEntry]:
    """하네스 튜닝용. DEBUG=true일 때만 열린다. 닫혀 있으면 owner 검사 전에 없는 경로와 같은 404다."""
    state, _ = _load(registry, store, session_id, owner)
    return state.trace
