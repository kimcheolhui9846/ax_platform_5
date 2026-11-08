"""사용자에게 보이는 실패 문구. 같은 실패에는 하네스·API·뷰가 모두 이 상수를 쓴다.

내부 사정(제공자 원문 오류, 예외 repr, 요청 검증 상세)은 여기 문구에 싣지 않고 trace·로그에만 남긴다.
"""

from collections.abc import Iterable

GENERATION_FAILED_MESSAGE = "결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요."
PROVIDER_FAILED_MESSAGE = "AI 호출에 실패했습니다. 다시 시도해 주세요."
AI_BUSY_MESSAGE = "지금 요청이 많아요. 잠시 후 다시 시도해 주세요."
INVALID_REQUEST_MESSAGE = "요청 형식이 올바르지 않습니다."
INTERNAL_ERROR_MESSAGE = "서버에서 문제가 생겼습니다. 잠시 후 다시 시도해 주세요."

SESSION_NOT_FOUND_MESSAGE = "세션을 찾을 수 없습니다."
RESULT_NOT_READY_MESSAGE = "아직 생성된 결과가 없습니다."
VERSION_NOT_FOUND_MESSAGE = "그 버전을 찾을 수 없습니다."
PREVIOUS_SESSION_NOT_FOUND_MESSAGE = "이어 갈 이전 작업을 찾을 수 없습니다."
SECTION_NOT_FOUND_MESSAGE = "그 섹션을 찾을 수 없습니다."
IMAGE_FAILED_MESSAGE = "참고 이미지를 만들지 못했어요. 결과 글은 그대로예요."
ASSET_NOT_FOUND_MESSAGE = "그 파일을 찾을 수 없습니다."
CLIENT_ID_REQUIRED_MESSAGE = "사용자 식별 정보(X-Client-Id 헤더)가 없거나 형식이 맞지 않습니다."


NOTICE_REQUIRED_MESSAGE = "외부 전송 안내를 확인해 주세요."


def private_unknown_message(names: Iterable[str]) -> str:
    return f"비공개로 정할 수 없는 항목입니다: {', '.join(names)}"


def unknown_task_message(task_type: str) -> str:
    return f"없는 과제입니다: {task_type}"


# 라우터가 detail 없이 낸 HTTP 오류(없는 경로, 허용되지 않는 메서드 등)의 상태별 문구
HTTP_STATUS_MESSAGES: dict[int, str] = {
    400: "잘못된 요청입니다.",
    401: "인증이 필요합니다.",
    403: "접근할 수 없습니다.",
    404: "찾을 수 없습니다.",
    405: "허용되지 않는 요청입니다.",
    413: "요청이 너무 큽니다.",
    429: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
}
HTTP_ERROR_FALLBACK_MESSAGE = "요청을 처리하지 못했습니다."

EVIDENCE_NOT_FOUND_MESSAGE = "그 근거 자료를 찾을 수 없습니다."
EVIDENCE_NO_RECORD_MESSAGE = "결과에 반영할 점검 문구가 없는 자료입니다."

PROMPT_LEAK_MESSAGE = "AI 응답에 내부 지침이 섞여 나와 반영하지 않았어요. 요청 글이나 답에 AI에게 내리는 지시가 있으면 빼고 다시 시도해 주세요."

INVENTORY_ITEM_NOT_FOUND_MESSAGE = "그 품목을 찾을 수 없습니다."
INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE = "그 거래처를 찾을 수 없습니다."
INVENTORY_UNKNOWN_SUPPLIER_MESSAGE = "없는 거래처를 골랐습니다."
INVENTORY_UNKNOWN_ITEM_MESSAGE = "없거나 숨긴 품목이 들어 있습니다."
INVENTORY_UNIT_LOCKED_MESSAGE = "수량 기록이 있는 품목은 단위를 바꿀 수 없습니다. 새 품목으로 등록해 주세요."
INVENTORY_TARGET_BELOW_MIN_MESSAGE = "목표 재고는 최소 재고보다 작을 수 없습니다."
INVENTORY_EMPTY_CLOSE_MESSAGE = "마감할 수량이나 조정을 하나 이상 입력해 주세요."
INVENTORY_ADJUST_UNCOUNTED_MESSAGE = "수량을 센 적 없는 품목은 조정할 수 없습니다. 먼저 수량을 입력해 주세요."
INVENTORY_NEGATIVE_STOCK_MESSAGE = "조정하면 수량이 0보다 작아집니다."
INVENTORY_ZERO_ADJUST_MESSAGE = "조정 값은 0일 수 없습니다."


def duplicate_item_message(name: str) -> str:
    return f"같은 품목이 이미 있습니다: {name}"


def unconfirmed_anomaly_message(names: Iterable[str]) -> str:
    return f"확인이 필요한 수량이 있습니다: {', '.join(names)}"

INVENTORY_ORDER_NOT_FOUND_MESSAGE = "그 주문을 찾을 수 없습니다."
INVENTORY_HOLD_NOT_FOUND_MESSAGE = "그 보류 내역을 찾을 수 없습니다."
INVENTORY_ADDRESS_REQUIRED_MESSAGE = "배송지를 먼저 설정해 주세요."
INVENTORY_NOT_ORDERABLE_MESSAGE = "주문할 수 없는 품목이 있습니다. 거래처가 정해진 구매 품목이어야 합니다."
INVENTORY_POLICY_REQUIRED_MESSAGE = "먼저 배송 기간과 단가를 넣은 보충 기준을 저장해 주세요."
INVENTORY_DUPLICATE_LINE_MESSAGE = "같은 품목이 주문에 두 번 들어 있습니다."
INVENTORY_MIXED_SUPPLIER_MESSAGE = "한 주문에는 한 거래처의 품목만 담을 수 있습니다."
INVENTORY_ORDER_NOT_RECEIVABLE_MESSAGE = "접수된 주문만 입고할 수 있습니다."
INVENTORY_RECEIPT_ITEM_MESSAGE = "이 주문에 없는 품목입니다."
INVENTORY_OVER_RECEIPT_MESSAGE = "남은 수량보다 많이 입고할 수 없습니다."
INVENTORY_CONSENT_REQUIRED_MESSAGE = "자동 주문을 켜려면 동의가 필요합니다."
INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE = "적용할 AI 추천이 없습니다. 먼저 추천을 받아 주세요."
