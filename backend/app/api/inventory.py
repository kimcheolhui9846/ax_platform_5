"""재고 API. 상태 변경은 app/inventory/service.py, 응답은 app/inventory/views.py가 한다."""
from fastapi import APIRouter

from app.api.responses import error_responses

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], responses=error_responses(500))
