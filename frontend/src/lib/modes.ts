import type { CoachingMode } from "../api/types";

type ModeCopy = { name: string; headline: string; detail: string };

/** 모드 카드 문구(디자인 수정본). 질문 수는 쓰지 않는다(상한은 질문 화면의 진행 표시가 알린다). */
export const MODE_COPY: Record<CoachingMode, ModeCopy> = {
  quick: {
    name: "빠른",
    headline: "핵심만 빠르게 정리해요",
    detail: "꼭 필요한 질문으로 방향을 잡고, 주요 기준을 확인해 초안을 만들어요.",
  },
  standard: {
    name: "스탠다드",
    headline: "단계별로 함께 구체화해요",
    detail: "질문을 주고받으며 아이디어와 실행 기준을 차근차근 구체화해요.",
  },
  precise: {
    name: "정밀",
    headline: "배경과 조건까지 깊이 살펴봐요",
    detail: "배경과 세부 조건을 살펴보며, 제약과 판단 근거까지 확인해요.",
  },
};

export const RECOMMENDED_MODE: CoachingMode = "standard";

export function modeName(mode: CoachingMode): string {
  return MODE_COPY[mode].name;
}
