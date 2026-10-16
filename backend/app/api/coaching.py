"""코칭 API. 설계서 10.1 엔드포인트 + 이전 답변 수정 + 세션 조회 + 디버그 trace."""
from fastapi import APIRouter, HTTPException, Request

from app.api.deps import Registry, Store
from app.api.views import to_result_view, to_session_view, to_task_form, to_task_summary
from app.core.state import Answer, SessionState, TraceEntry
from app.harness.base import BaseHarness
from app.harness.errors import GenerationFailed, UnknownTaskError
from app.schemas.coaching import (
    AnswerRequest,
    CreateSessionRequest,
    ResultView,
    ReviseAnswerRequest,
    SessionView,
    TaskForm,
    TaskSummary,
)

router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"])


def _harness(registry: Registry, task_type: str) -> BaseHarness:
    try:
        return registry.get(task_type)
    except UnknownTaskError:
        raise HTTPException(status_code=404, detail=f"없는 과제입니다: {task_type}") from None


def _load(registry: Registry, store: Store, session_id: str) -> tuple[SessionState, BaseHarness]:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return state, _harness(registry, state.task_type)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(registry: Registry) -> list[TaskSummary]:
    return [to_task_summary(h) for h in registry.all()]


@router.get("/tasks/{task_type}/form", response_model=TaskForm)
def get_task_form(task_type: str, registry: Registry) -> TaskForm:
    return to_task_form(_harness(registry, task_type))


@router.post("/tasks/{task_type}/sessions", response_model=SessionView, status_code=201)
def create_session(
    task_type: str, body: CreateSessionRequest, registry: Registry, store: Store
) -> SessionView:
    harness = _harness(registry, task_type)
    state = harness.start(body.raw_input, body.mode)
    store.save(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}", response_model=SessionView)
def get_session(session_id: str, registry: Registry, store: Store) -> SessionView:
    state, harness = _load(registry, store, session_id)
    return to_session_view(state, harness)


@router.post("/sessions/{session_id}/answers", response_model=SessionView)
def submit_answer(
    session_id: str, body: AnswerRequest, registry: Registry, store: Store
) -> SessionView:
    state, harness = _load(registry, store, session_id)
    harness.apply_answer(state, Answer(**body.model_dump()))
    store.save(state)
    return to_session_view(state, harness)


@router.patch("/sessions/{session_id}/answers/{question_id}", response_model=SessionView)
def revise_answer(
    session_id: str, question_id: str, body: ReviseAnswerRequest, registry: Registry, store: Store
) -> SessionView:
    state, harness = _load(registry, store, session_id)
    harness.revise_answer(state, Answer(question_id=question_id, **body.model_dump()))
    store.save(state)
    return to_session_view(state, harness)


@router.post("/sessions/{session_id}/generate", response_model=ResultView)
def generate(session_id: str, registry: Registry, store: Store) -> ResultView:
    state, harness = _load(registry, store, session_id)
    try:
        harness.generate(state)
    except GenerationFailed:
        store.save(state)
        raise HTTPException(
            status_code=502,
            detail="결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요.",
        ) from None
    store.save(state)
    return to_result_view(state)


@router.get("/sessions/{session_id}/result", response_model=ResultView)
def get_result(session_id: str, registry: Registry, store: Store) -> ResultView:
    state, _ = _load(registry, store, session_id)
    if state.result is None:
        raise HTTPException(status_code=404, detail="아직 생성된 결과가 없습니다.")
    return to_result_view(state)


@router.get("/sessions/{session_id}/trace", response_model=list[TraceEntry])
def get_trace(session_id: str, request: Request, registry: Registry, store: Store) -> list[TraceEntry]:
    """하네스 튜닝용. DEBUG=true일 때만 열린다."""
    if not request.app.state.debug:
        raise HTTPException(status_code=404, detail="Not Found")
    state, _ = _load(registry, store, session_id)
    return state.trace
