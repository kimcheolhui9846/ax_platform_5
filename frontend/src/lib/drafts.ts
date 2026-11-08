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

// 보내기 전 입력 초안(질문 직접 답변·답 고치기·결과 문구 고치기). 요청 글과 같은 원칙이고 키가 다르다.
const INPUT_PREFIX = "ax.draft.input.";

export const answerDraftKey = (sessionId: string, questionId: string): string => `answer:${sessionId}:${questionId}`;
export const reviseDraftKey = (sessionId: string, questionId: string): string => `revise:${sessionId}:${questionId}`;
export const sectionDraftKey = (sessionId: string, order: number): string => `section:${sessionId}:${order}`;

/** 요청 글 초안의 키는 과제 이름이고, 입력 초안의 키는 위 함수들이 만든다(콜론이 들어 있다). */
export const isInputDraftKey = (key: string): boolean => key.includes(":");

export function readInputDraft(storage: KeyValueStore | null, key: string): string {
  try {
    return storage?.getItem(INPUT_PREFIX + key) ?? "";
  } catch {
    return "";
  }
}

/** text가 null이거나 비면 지운다. */
export function writeInputDraft(storage: KeyValueStore | null, key: string, text: string | null): void {
  try {
    if (text) storage?.setItem(INPUT_PREFIX + key, text);
    else storage?.removeItem(INPUT_PREFIX + key);
  } catch {
    // 저장하지 못해도 화면의 글은 남는다
  }
}

/** [순수] 앱 상태의 초안이 prev에서 next로 바뀐 만큼 저장소에 할 일(입력 초안만). text null은 지우기다. */
export function inputDraftWrites(prev: Record<string, string>, next: Record<string, string>): { key: string; text: string | null }[] {
  const writes: { key: string; text: string | null }[] = [];
  for (const key of Object.keys(next)) {
    if (isInputDraftKey(key) && next[key] !== prev[key]) writes.push({ key, text: next[key] });
  }
  for (const key of Object.keys(prev)) {
    if (isInputDraftKey(key) && !(key in next)) writes.push({ key, text: null });
  }
  return writes;
}
