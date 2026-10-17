import type { LabeledResult, ResultSection, ResultView, TaskSummary, ValidationIssue, VersionSummary } from "../api/types";
import { criteriaRows } from "./criteria";
import type { CriteriaRow } from "./criteria";
import { cardLabel } from "./labels";
import { versionLine } from "./sessions";
import { appliedRows } from "./supplements";
import type { AppliedRow } from "./supplements";

export type DocumentSection = { key: string; number: string; heading: string; tag: string; body: string };

/** [순수] 섹션의 글 블록을 이어 붙인 본문. */
export function sectionText(section: Pick<ResultSection, "blocks">): string {
  return section.blocks
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n\n");
}

/** [순수] 결과 섹션을 문서 섹션(순서대로 01, 02 …)으로. */
export function documentSections(sections: ResultSection[]): DocumentSection[] {
  return [...sections]
    .sort((a, b) => a.order - b.order)
    .map((section, index) => ({
      key: `${section.kind}-${section.order}`,
      number: String(index + 1).padStart(2, "0"),
      heading: section.heading,
      tag: cardLabel(section.kind),
      body: sectionText(section),
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
export type Shown = Pick<ResultView, "result" | "validation" | "version" | "summary" | "unknowns" | "supplements">;

export type DocumentContent = {
  title: string;
  kicker: string;
  rows: CriteriaRow[];
  result: LabeledResult;
  issues: ValidationIssue[];
  supplements: AppliedRow[]; // 그 결과에 반영한 보완 정보(사용자 입력·검증 전)
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
    supplements: appliedRows(shown.supplements),
  };
}

/** [순수] 첫 섹션(순서가 가장 앞선 섹션)의 번호. 결과 화면의 '소개 문구 수정하기'가 연다. 섹션이 없으면 null. */
export function firstSectionOrder(sections: Pick<ResultSection, "order">[]): number | null {
  return sections.length === 0 ? null : Math.min(...sections.map((s) => s.order));
}
