class HarnessError(Exception):
    """사용자 입력이 하네스 규칙에 맞지 않는다 (API에서 422)."""


class GenerationFailed(Exception):
    """결과 생성이 실패했다. 세션 입력은 보존된다 (API에서 502)."""


class UnknownTaskError(LookupError):
    """등록되지 않은 과제 유형이다 (API에서 404)."""
