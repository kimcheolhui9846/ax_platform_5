const MAX_LENGTH = 40;
// eslint-disable-next-line no-control-regex
const FORBIDDEN = /[\\/:*?"<>|\u0000-\u001f\u007f]/g;

/** [순수] 작업 이름을 파일 이름으로 쓸 수 있게 다듬는다. 금지 문자·제어문자를 빼고 공백을 접고 40자로 자른다. 비면 fallback. */
export function safeFileName(name: string, fallback: string): string {
  const cleaned = name
    .replace(/[\s]+/g, " ")
    .replace(FORBIDDEN, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_LENGTH)
    .replace(/[\s.]+$/, "");
  return cleaned === "" ? fallback : cleaned;
}
