"""요청한 사용자(owner). 지금은 브라우저가 만든 익명 ID(X-Client-Id 헤더)다.

로그인을 붙일 때는 current_owner 하나만 바꾼다(익명 ID의 작업은 그때 계정으로 옮긴다).
"""
import re
from typing import Annotated

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.messages import CLIENT_ID_REQUIRED_MESSAGE

CLIENT_ID_HEADER = "X-Client-Id"
_CLIENT_ID = re.compile(r"[A-Za-z0-9-]{8,64}")  # 프론트 lib/clientId.ts와 같은 형식

client_id_header = APIKeyHeader(
    name=CLIENT_ID_HEADER,
    scheme_name="ClientId",
    description="브라우저가 처음 접속할 때 만든 익명 사용자 ID",
    auto_error=False,
)


def parse_owner(value: str | None) -> str | None:
    """[순수] 헤더 값이 익명 ID 형식이면 그 값, 아니면 None."""
    return value if value is not None and _CLIENT_ID.fullmatch(value) else None


def current_owner(value: Annotated[str | None, Security(client_id_header)]) -> str:
    owner = parse_owner(value)
    if owner is None:
        raise HTTPException(status_code=422, detail=CLIENT_ID_REQUIRED_MESSAGE)
    return owner
