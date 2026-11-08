"""재고 예외. 메시지는 사용자에게 보이는 한국어 문장(app/core/messages.py)이다. 처리기는 app/api/errors.py."""


class InventoryError(Exception):
    """요청이 재고 규칙에 맞지 않음(422). 상태는 저장하지 않는다."""


class InventoryNotFound(Exception):
    """경로의 품목·거래처가 없음(404)."""
