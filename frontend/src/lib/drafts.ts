import type { KeyValueStore } from "./storage";

// 과제별 쓰다 만 요청 글. 브라우저에만 두는 편의 값이라 읽고 쓰기가 실패해도 화면은 그대로 동작한다.
const PREFIX = "ax.draft.request.";

export function readDraft(storage: KeyValueStore | null, task: string): string {
  try {
    return storage?.getItem(PREFIX + task) ?? "";
  } catch {
    return "";
  }
}

export function writeDraft(storage: KeyValueStore | null, task: string, text: string): void {
  try {
    if (text) storage?.setItem(PREFIX + task, text);
    else storage?.removeItem(PREFIX + task);
  } catch {
    // 저장하지 못해도 화면의 글은 남는다
  }
}
