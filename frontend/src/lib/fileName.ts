const MAX_LENGTH = 40;
// 탭·줄바꿈 같은 공백 문자는 지우지 않고 아래에서 공백 하나로 접는다
// eslint-disable-next-line no-control-regex
const FORBIDDEN = /[\\/:*?"<>|\u0000-\u0008\u000e-\u001f\u007f]/g;

/** [순수] 작업 이름을 파일 이름으로 쓸 수 있게 다듬는다. 금지 문자·제어문자를 빼고 공백을 접고 40자로 자른다. 비면 fallback. */
export function safeFileName(name: string, fallback: string): string {
  const cleaned = Array.from(
    name
      .replace(FORBIDDEN, "")
      .replace(/\s+/g, " ")
      .trim(),
  )
    .slice(0, MAX_LENGTH) // 코드 포인트 단위로 잘라 이모지 같은 짝 문자를 반으로 가르지 않는다
    .join("")
    .replace(/[\s.]+$/, "");
  return cleaned === "" ? fallback : cleaned;
}
