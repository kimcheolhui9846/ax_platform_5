import type { TaskSummary } from "../api/types";

/** 이어 갈 이전 작업(세션과 그 버전). */
export type CarrySource = { sessionId: string; version: number };

/** [순수] 과제 순서에서 다음 과제(마지막 다음은 처음). 과제가 하나뿐이거나 모르는 과제면 null. */
export function nextTask(tasks: TaskSummary[], current: string): TaskSummary | null {
  const index = tasks.findIndex((t) => t.task_type === current);
  if (index < 0 || tasks.length < 2) return null;
  return tasks[(index + 1) % tasks.length];
}

/** [순수] 이 미리보기가 그 세션을 이어 가는 것인가(키의 가운데 조각이 세션 id다). */
export function carryIsFrom(key: string, sessionId: string): boolean {
  return key.split(":")[1] === sessionId;
}

/** [순수] 미리보기 하나를 가리키는 이름(과제·이전 작업·버전). */
export function carryKey(task: string, from: CarrySource): string {
  return `${task}:${from.sessionId}:${from.version}`;
}
