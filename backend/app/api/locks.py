"""세션별 잠금. 같은 세션을 바꾸는 요청(답변·수정·생성)을 한 번에 하나씩 처리한다.

라우터는 동기 함수라 스레드 풀에서 돈다. 잠그지 않으면 같은 세션에 겹친 두 요청이 각자 읽은 상태로
계산한 뒤 나중에 저장한 쪽이 앞선 변경을 덮어쓴다. 읽기 → 하네스 → 저장 전체를 잠근다.
잠금은 라우터가 세션이 있는지 확인한 뒤에만 만들므로 많아야 세션 수만큼 남는다(메모리 저장소와 같은 수명).
없는 id로 요청해도 늘지 않는다. 여러 프로세스로 띄우면 저장소 쪽 잠금이 필요하다.
"""
import threading
from collections.abc import Iterator
from contextlib import contextmanager


class SessionLocks:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    def _lock_for(self, session_id: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(session_id, threading.Lock())

    @contextmanager
    def hold(self, session_id: str) -> Iterator[None]:
        with self._lock_for(session_id):
            yield

    def __len__(self) -> int:
        """지금까지 만든 잠금 수(세션 수를 넘지 않아야 한다)."""
        return len(self._locks)

    def is_held(self, session_id: str) -> bool:
        lock = self._locks.get(session_id)
        return lock is not None and lock.locked()
