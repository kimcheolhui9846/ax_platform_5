import type { LabeledResult, ResultCard, ResultView, TaskSummary, ValidationIssue, VersionSummary } from "../api/types";
import { criteriaRows } from "./criteria";
import type { CriteriaRow } from "./criteria";
import { cardLabel } from "./labels";
import { versionLine } from "./sessions";

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

/** 결과 문서 위 작은 줄: "V2 · 다시 만든 초안 / 결과물 이름". 지금 답과 맞지 않으면 함께 알린다. */
export function resultKicker(deliverable: string, version: Pick<VersionSummary, "version" | "reason">, stale: boolean): string {
  const line = `${versionLine(version)} / ${deliverable}`;
  return stale ? `${line} · 최신 아님` : line;
}

/** 문서로 보여 줄 결과. 지금 결과(ResultView)와 지난 버전(VersionView)이 같은 모양이다. */
export type Shown = Pick<ResultView, "result" | "validation" | "version" | "summary" | "unknowns">;

export type DocumentContent = {
  title: string;
  kicker: string;
  rows: CriteriaRow[];
  result: LabeledResult;
  issues: ValidationIssue[];
};

/** [순수] 화면의 결과 문서와 내려받는 문서가 같이 쓰는 내용. 기준은 그 결과를 만든 버전의 것이다. */
export function documentContent(
  task: Pick<TaskSummary, "title" | "deliverable">,
  shown: Shown,
  stale: boolean,
): DocumentContent {
  return {
    title: resultTitle(task.title),
    kicker: resultKicker(task.deliverable, shown.version, stale),
    rows: criteriaRows(shown.summary, shown.unknowns),
    result: shown.result,
    issues: shown.validation?.issues ?? [],
  };
}
