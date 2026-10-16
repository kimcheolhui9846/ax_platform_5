import type { LabeledAssumption } from "../api/types";

type Shown = Pick<LabeledAssumption, "label" | "value" | "requires_confirmation">;

/** AI 가정 한 줄. 내부 필드 이름이 아니라 라벨을 보여 준다. */
export function formatAssumption({ label, value, requires_confirmation }: Shown): string {
  return requires_confirmation ? `${label}: ${value} (확인 필요)` : `${label}: ${value}`;
}

/** LLM이 같은 필드를 두 번 적어도 겹치지 않는 목록 키. */
export function assumptionKey({ field }: Pick<LabeledAssumption, "field">, index: number): string {
  return `${index}-${field}`;
}
