import type { CoachingMode } from "../api/types";

type ModeCopy = { name: string; headline: string; detail: (cap: number) => string };

/** 모드 카드 문구(디자인 V2). 질문 수는 상한이라 "최대 N개"로 쓴다(설계 §1의 2). */
export const MODE_COPY: Record<CoachingMode, ModeCopy> = {
  quick: {
    name: "빠른",
    headline: "핵심만 빠르게 정리해요",
    detail: (cap) => `핵심 질문 위주로 최대 ${cap}개까지 물어요. 주요 기준을 확인하고 초안을 만들어요.`,
  },
  standard: {
    name: "스탠다드",
    headline: "단계별로 함께 구체화해요",
    detail: (cap) => `핵심 질문과 추가 질문을 최대 ${cap}개까지 물어요. 실행 기준을 한 단계 더 구체화해요.`,
  },
  precise: {
    name: "정밀",
    headline: "배경과 조건까지 깊이 살펴봐요",
    detail: (cap) => `핵심 · 추가 · 세부 질문을 최대 ${cap}개까지 물어요. 조건과 제약까지 함께 확인해요.`,
  },
};

export const RECOMMENDED_MODE: CoachingMode = "standard";

export function modeName(mode: CoachingMode): string {
  return MODE_COPY[mode].name;
}
