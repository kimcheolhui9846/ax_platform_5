import type { ResultCard } from "../api/types";
import { cardLabel } from "./labels";

export type DocumentSection = { key: string; number: string; heading: string; tag: string; body: string };

/** [순수] 결과 카드를 문서 섹션(순서대로 01, 02 …)으로. */
export function documentSections(cards: ResultCard[]): DocumentSection[] {
  return [...cards]
    .sort((a, b) => a.order - b.order)
    .map((card, index) => ({
      key: `${card.card_type}-${card.order}`,
      number: String(index + 1).padStart(2, "0"),
      heading: card.title,
      tag: cardLabel(card.card_type),
      body: card.body,
    }));
}

export function resultTitle(taskTitle: string): string {
  return `${taskTitle} 초안`;
}

/** 결과 문서 위 작은 줄. 결과가 지금 답과 맞지 않으면 함께 알린다. */
export function resultKicker(deliverable: string, stale: boolean): string {
  return stale ? `${deliverable} · 최신 아님` : deliverable;
}
