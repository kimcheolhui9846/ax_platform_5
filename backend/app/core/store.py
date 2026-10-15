"""세션 저장소. 지금은 메모리 구현만 있다."""
from typing import Protocol

from app.core.results import utcnow
from app.core.state import SessionState


class SessionStore(Protocol):
    def get(self, session_id: str) -> SessionState | None: ...

    def save(self, state: SessionState) -> None: ...


class InMemorySessionStore:
    """서버를 재시작하면 사라진다. 영속화가 필요해지면 같은 인터페이스로 SQLite 구현을 추가한다."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState | None:
        state = self._sessions.get(session_id)
        return state.model_copy(deep=True) if state else None

    def save(self, state: SessionState) -> None:
        state.updated_at = utcnow()
        self._sessions[state.session_id] = state.model_copy(deep=True)
