/** 외부 AI 전송 고지 문구. 서버가 세션을 만들 때 확인 여부(notice_acknowledged)를 요구한다.
 * 문구를 바꾸면 backend `app/harness/privacy.py`의 NOTICE_VERSION도 올린다(짝). */
export const NOTICE_TEXT =
  "입력 내용은 결과를 만들기 위해 외부 AI 서비스로 전송될 수 있어요. 개인정보(주민번호·연락처·계좌 등)는 자동으로 가려서 보내고, 'AI에 보내지 않음'으로 표시한 항목은 보내지 않아요. 공개 전 아이디어·영업비밀은 표시해 주세요.";

/** [순수] 이 항목이 AI에 보내지 않음으로 정해져 있는지. */
export function isPrivate(privateNames: string[], name: string): boolean {
  return privateNames.includes(name);
}

/** [순수] 처음 값과 달라진 항목만 돌려준다(서버에 바뀐 것만 보낸다). */
export function privateChanges(initial: Record<string, boolean>, current: Record<string, boolean>): Record<string, boolean> {
  return Object.fromEntries(Object.entries(current).filter(([name, value]) => initial[name] !== value));
}

/** 기준 표에서 AI에 보내지 않은 항목 옆에 붙이는 표시. */
export const PRIVATE_LABEL = "AI에 보내지 않음";
