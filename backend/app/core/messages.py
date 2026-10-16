"""사용자에게 보이는 실패 문구. 같은 실패에는 하네스·API·뷰가 모두 이 상수를 쓴다.

내부 사정(제공자 원문 오류, 예외 repr)은 여기 문구에 싣지 않고 trace·로그에만 남긴다.
"""

GENERATION_FAILED_MESSAGE = "결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요."
PROVIDER_FAILED_MESSAGE = "AI 호출에 실패했습니다. 다시 시도해 주세요."
INVALID_REQUEST_MESSAGE = "요청 형식이 올바르지 않습니다."
