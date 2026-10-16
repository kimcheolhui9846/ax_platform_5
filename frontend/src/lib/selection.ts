/** 선택지 토글. 단일 선택이면 방금 고른 것만, 다중 선택이면 추가/제거한다. */
export function toggleSelection(selected: string[], id: string, multi: boolean): string[] {
  if (!multi) return [id];
  return selected.includes(id) ? selected.filter((v) => v !== id) : [...selected, id];
}
