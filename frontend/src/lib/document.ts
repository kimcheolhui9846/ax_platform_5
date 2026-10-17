import type { EvidenceRecord, LabeledResult, ResultSection, ResultView, TaskSummary, ValidationIssue, VersionSummary } from "../api/types";
import { criteriaRows } from "./criteria";
import type { CriteriaRow } from "./criteria";
import { safeUrl } from "./evidence";
import { cardLabel } from "./labels";
import { versionLine } from "./sessions";
import { appliedRows } from "./supplements";
import type { AppliedRow } from "./supplements";

/** asset_id → data URL. null은 불러오는 중이거나 불러오지 못했다(대체 글을 보인다). */
export type Images = Record<string, string | null>;

export type DocumentBlock =
  | { kind: "text"; key: string; text: string }
  | { kind: "image"; key: string; src: string | null; alt: string; caption: string };

export type DocumentRecord = { key: string; label: string; text: string; source: string; note: string; url: string | null };

export type DocumentSection = { key: string; number: string; heading: string; tag: string; blocks: DocumentBlock[]; records: DocumentRecord[] };

/** [순수] 섹션의 글 블록을 이어 붙인 본문. */
export function sectionText(section: Pick<ResultSection, "blocks">): string {
  return section.blocks
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n\n");
}

function documentBlocks(section: ResultSection, images: Images): DocumentBlock[] {
  return section.blocks.map((block, index) =>
    block.type === "text"
      ? { kind: "text", key: String(index), text: block.text }
      : { kind: "image", key: String(index), src: images[block.asset_id] ?? null, alt: block.alt, caption: block.caption },
  );
}

function documentRecord(record: EvidenceRecord): DocumentRecord {
  return {
    key: record.source_id,
    label: `근거 검토 반영 · ${record.title}`,
    text: record.text,
    source: `출처: ${record.publisher} · ${record.source_title}`,
    note: record.note,
    url: safeUrl(record.url),
  };
}

/** [순수] 결과 섹션을 문서 섹션(순서대로 01, 02 …)으로. 근거 기록은 자리 잡은 섹션에 붙인다. */
export function documentSections(sections: ResultSection[], evidence: EvidenceRecord[], images: Images): DocumentSection[] {
  return [...sections]
    .sort((a, b) => a.order - b.order)
    .map((section, index) => ({
      key: `${section.kind}-${section.order}`,
      number: String(index + 1).padStart(2, "0"),
      heading: section.heading,
      tag: cardLabel(section.kind),
      blocks: documentBlocks(section, images),
      records: evidence.filter((r) => r.section_order === section.order).map(documentRecord),
    }));
}

/** [순수] 자리 잡을 섹션이 없는 근거 기록(문서 끝에 둔다). */
export function trailingRecords(sections: ResultSection[], evidence: EvidenceRecord[]): DocumentRecord[] {
  const orders = new Set(sections.map((s) => s.order));
  return evidence.filter((r) => r.section_order === null || !orders.has(r.section_order)).map(documentRecord);
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
  images: Images;
  trailing: DocumentRecord[]; // 자리 잡을 섹션이 없는 근거 기록
};

/** [순수] 화면의 결과 문서와 내려받는 문서가 같이 쓰는 내용. 기준은 그 결과를 만든 버전의 것이다. */
export function documentContent(
  task: Pick<TaskSummary, "title" | "deliverable">,
  shown: Shown,
  stale: boolean,
  images: Images,
): DocumentContent {
  return {
    title: resultTitle(task.title),
    kicker: resultKicker(task.deliverable, shown.version, stale),
    rows: criteriaRows(shown.summary, shown.unknowns),
    result: shown.result,
    issues: shown.validation?.issues ?? [],
    supplements: appliedRows(shown.supplements),
    images,
    trailing: trailingRecords(shown.result.sections, shown.result.evidence),
  };
}

/** [순수] 첫 섹션(순서가 가장 앞선 섹션)의 번호. 결과 화면의 '소개 문구 수정하기'가 연다. 섹션이 없으면 null. */
export function firstSectionOrder(sections: Pick<ResultSection, "order">[]): number | null {
  return sections.length === 0 ? null : Math.min(...sections.map((s) => s.order));
}
