"""사용자에게 보이는 실패 문구. 같은 실패에는 하네스·API·뷰가 모두 이 상수를 쓴다.

내부 사정(제공자 원문 오류, 예외 repr, 요청 검증 상세)은 여기 문구에 싣지 않고 trace·로그에만 남긴다.
"""

GENERATION_FAILED_MESSAGE = "결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요."
PROVIDER_FAILED_MESSAGE = "AI 호출에 실패했습니다. 다시 시도해 주세요."
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
