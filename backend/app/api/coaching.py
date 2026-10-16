"""코칭 API. 설계서 10.1 엔드포인트 + 이전 답변 수정 + 세션 조회 + 디버그 trace."""
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import Locks, Registry, Store
from app.api.locks import SessionLocks
from app.api.responses import error_responses
from app.api.views import to_result_view, to_session_view, to_task_form, to_task_summary
from app.core.messages import (
    RESULT_NOT_READY_MESSAGE,
    SESSION_NOT_FOUND_MESSAGE,
    unknown_task_message,
)
from app.core.state import Answer, SessionState, TraceEntry
from app.core.store import SessionStore
from app.harness.base import BaseHarness
from app.harness.errors import GenerationFailed, HarnessError, UnknownTaskError
from app.providers.base import ProviderError
from app.schemas.coaching import (
    AnswerRequest,
    CreateSessionRequest,
    ResultView,
    ReviseAnswerRequest,
    SessionView,
    TaskForm,
    TaskSummary,
)

# 오류 본문은 app/api/errors.py가 모두 ErrorBody 모양으로 만든다. 경로마다 낼 수 있는 오류만 선언하고
# 500은 어디서나 날 수 있어 라우터 공통으로 둔다.
router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"], responses=error_responses(500))


def _harness(registry: Registry, task_type: str) -> BaseHarness:
    try:
        return registry.get(task_type)
    except UnknownTaskError:
        raise HTTPException(status_code=404, detail=unknown_task_message(task_type)) from None


def _load(registry: Registry, store: Store, session_id: str) -> tuple[SessionState, BaseHarness]:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail=SESSION_NOT_FOUND_MESSAGE)
    return state, _harness(registry, state.task_type)


@contextmanager
def _session_update(
    locks: SessionLocks, registry: Registry, store: SessionStore, session_id: str
) -> Iterator[tuple[SessionState, BaseHarness]]:
    """세션을 잠그고 읽어 블록에 넘긴 뒤 저장한다. 같은 세션을 바꾸는 요청은 한 번에 하나씩 돈다.

    AI 호출·생성 실패(502)나 입력·규칙 문제(HarnessError, 422)로 끝나도 그때의 state를 저장하고 오류를 다시
    던진다. 하네스는 이런 실패에서 state를 시작 때로 되돌리고 trace(성공한 LLM 호출 기록 포함)와 FAILED 표시만
    남기므로, 저장해도 바뀌는 것은 그 기록뿐이다. 응답 문구는 app/api/errors.py의 예외 처리기가 정한다.

    잠금은 있는 세션에만 만든다. 없는 id는 잠그기 전에 404로 끝낸다(세션은 지우지 않으므로 확인과 잠금 사이에
    사라질 일이 없다). 잠근 뒤 다시 읽어 앞선 요청이 저장한 최신 상태로 일한다.
    """
    _load(registry, store, session_id)
    with locks.hold(session_id):
        state, harness = _load(registry, store, session_id)
        try:
            yield state, harness
        except (ProviderError, GenerationFailed, HarnessError):
            store.save(state)
            raise
        store.save(state)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(registry: Registry) -> list[TaskSummary]:
    return [to_task_summary(h.policy) for h in registry.all()]


@router.get("/tasks/{task_type}/form", response_model=TaskForm, responses=error_responses(404))
def get_task_form(task_type: str, registry: Registry) -> TaskForm:
    return to_task_form(_harness(registry, task_type).policy)


@router.post(
    "/tasks/{task_type}/sessions",
    response_model=SessionView,
    status_code=201,
    responses=error_responses(404, 422, 502),
)
def create_session(
    task_type: str, body: CreateSessionRequest, registry: Registry, store: Store
) -> SessionView:
    harness = _harness(registry, task_type)
    state = harness.start(body.raw_input, body.mode)
    store.save(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}", response_model=SessionView, responses=error_responses(404))
def get_session(session_id: str, registry: Registry, store: Store) -> SessionView:
    state, harness = _load(registry, store, session_id)
    return to_session_view(state, harness)


@router.post(
    "/sessions/{session_id}/answers", response_model=SessionView, responses=error_responses(404, 422, 502)
)
def submit_answer(
    session_id: str, body: AnswerRequest, registry: Registry, store: Store, locks: Locks
) -> SessionView:
    with _session_update(locks, registry, store, session_id) as (state, harness):
        harness.apply_answer(state, Answer(**body.model_dump()))
    return to_session_view(state, harness)


@router.patch(
    "/sessions/{session_id}/answers/{question_id}",
    response_model=SessionView,
    responses=error_responses(404, 422, 502),
)
def revise_answer(
    session_id: str,
    question_id: str,
    body: ReviseAnswerRequest,
    registry: Registry,
    store: Store,
    locks: Locks,
) -> SessionView:
    with _session_update(locks, registry, store, session_id) as (state, harness):
        harness.revise_answer(state, Answer(question_id=question_id, **body.model_dump()))
    return to_session_view(state, harness)


@router.post(
    "/sessions/{session_id}/generate", response_model=ResultView, responses=error_responses(404, 422, 502)
)
def generate(session_id: str, registry: Registry, store: Store, locks: Locks) -> ResultView:
    with _session_update(locks, registry, store, session_id) as (state, harness):
        harness.generate(state)
    return to_result_view(state, harness.policy.labels)


@router.post(
    "/sessions/{session_id}/continue", response_model=SessionView, responses=error_responses(404, 502)
)
def continue_session(session_id: str, registry: Registry, store: Store, locks: Locks) -> SessionView:
    """결과를 만든 뒤 질문을 이어 간다. 남은 질문이 없으면 세션은 그대로다."""
    with _session_update(locks, registry, store, session_id) as (state, harness):
        harness.resume(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}/result", response_model=ResultView, responses=error_responses(404))
def get_result(session_id: str, registry: Registry, store: Store) -> ResultView:
    state, harness = _load(registry, store, session_id)
    if state.result is None:
        raise HTTPException(status_code=404, detail=RESULT_NOT_READY_MESSAGE)
    return to_result_view(state, harness.policy.labels)


@router.get(
    "/sessions/{session_id}/trace", response_model=list[TraceEntry], responses=error_responses(404)
)
def get_trace(session_id: str, request: Request, registry: Registry, store: Store) -> list[TraceEntry]:
    """하네스 튜닝용. DEBUG=true일 때만 열린다. 닫혀 있으면 없는 경로와 같은 404다."""
    if not request.app.state.debug:
        raise HTTPException(status_code=404)
    state, _ = _load(registry, store, session_id)
    return state.trace
