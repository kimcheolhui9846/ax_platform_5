import type { Progress } from "../api/types";

export function formatProgress({ asked, cap, readiness }: Progress): string {
  return `질문 ${asked}/${cap} · 준비도 ${Math.round(readiness * 100)}%`;
}
