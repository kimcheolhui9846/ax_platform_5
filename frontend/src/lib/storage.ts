/** 브라우저 저장소(localStorage). 편의 값(익명 ID·쓰다 만 글)만 둔다. */
export type KeyValueStore = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** 접근만으로 예외가 나는 환경(차단된 사이트 데이터, 일부 미리보기)이 있어 감싼다. 못 쓰면 null. */
export function browserStorage(): KeyValueStore | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}
