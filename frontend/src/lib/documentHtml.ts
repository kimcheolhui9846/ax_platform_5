import { formatAssumption } from "./assumption";
import type { DocumentBlock, DocumentContent, DocumentRecord } from "./document";
import { documentSections } from "./document";
import { PRIVATE_LABEL } from "./privacy";

export type DocumentFile = { filename: string; html: string };

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => ESCAPES[char]);
}

// 내려받은 파일은 앱 밖에서 열리므로 스타일을 파일 안에 둔다(인쇄해도 읽기 좋게).
const STYLE = [
  'body{font-family:"Noto Sans KR",sans-serif;max-width:760px;margin:40px auto;padding:0 16px;line-height:1.7;color:#202020}',
  "h1{font-size:28px;margin:4px 0 24px}h2{font-size:20px;margin:28px 0 8px}",
  "p{white-space:pre-line;margin:0 0 8px}.note{color:#707070;font-size:13px}.num{color:#800122;font-size:13px}",
  "table{border-collapse:collapse;width:100%}th,td{padding:6px 8px;border-top:1px solid #e0e0e0;text-align:left;vertical-align:top}",
  "th{width:120px;font-weight:500}",
  "figure{margin:12px 0}img{max-width:100%;height:auto}figcaption{color:#707070;font-size:13px}.record{background:#f4f4f4;padding:12px 16px;margin:12px 0}a{color:#707070}",
].join("");

function list(heading: string, items: string[]): string {
  if (items.length === 0) return "";
  return `<h2>${escapeHtml(heading)}</h2><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function blockHtml(block: DocumentBlock): string {
  const e = escapeHtml;
  if (block.kind === "text") return `<p>${e(block.text)}</p>`;
  if (block.src !== null && block.src.startsWith("data:image/")) {
    const caption = block.caption ? `<figcaption>${e(block.caption)}</figcaption>` : "";
    return `<figure><img src="${e(block.src)}" alt="${e(block.alt)}">${caption}</figure>`;
  }
  return `<p class="note">[이미지: ${e(block.alt)}]</p>`;
}

function recordHtml(record: DocumentRecord): string {
  const e = escapeHtml;
  const source = record.url ? `<a href="${e(record.url)}">${e(record.source)}</a>` : e(record.source);
  const note = record.note ? ` · ${e(record.note)}` : "";
  return `<div class="record"><p><strong>${e(record.label)}</strong></p><p>${e(record.text)}</p><p class="note">${source}${note}</p></div>`;
}

/** [순수] 내려받을 결과 문서(HTML 한 파일). 사용자·AI가 쓴 글은 모두 이스케이프한다. 이미지가 들어갈 수 있어 HTML이다. */
export function documentHtml(content: DocumentContent & { request: string }): string {
  const e = escapeHtml;
  const rows = content.rows
    .map((row) => `<tr><th>${e(row.label)}</th><td>${e(row.value)}${row.note ? ` <span class="note">· ${e(row.note)}</span>` : ""}${row.private ? ` <span class="note">· ${e(PRIVATE_LABEL)}</span>` : ""}</td></tr>`)
    .join("");
  const sections = documentSections(content.result.sections, content.result.evidence, content.images)
    .map(
      (s) =>
        `<h2><span class="num">${s.number}</span> ${e(s.heading)} <span class="note">${e(s.tag)}</span></h2>${s.blocks.map(blockHtml).join("")}${s.records.map(recordHtml).join("")}`,
    )
    .join("");
  const supplements =
    content.supplements.length === 0
      ? ""
      : `<h2>보완 정보 · 사용자 입력 / 검증 전</h2><table>${content.supplements
          .map((row) => `<tr><th>${e(row.label)}</th><td>${e(row.value)}</td></tr>`)
          .join("")}</table>`;
  return [
    "<!doctype html>",
    '<html lang="ko">',
    "<head>",
    '<meta charset="utf-8">',
    `<title>${e(content.title)}</title>`,
    `<style>${STYLE}</style>`,
    "</head>",
    "<body>",
    `<p class="note">${e(content.kicker)}</p>`,
    `<h1>${e(content.title)}</h1>`,
    "<h2>내 요청</h2>",
    `<p>${e(content.request)}</p>`,
    "<h2>내 답변에서 반영한 기준</h2>",
    `<table>${rows}</table>`,
    sections,
    content.trailing.map(recordHtml).join(""),
    supplements,
    list("AI가 가정한 내용", content.result.assumptions.map(formatAssumption)),
    list("검토가 필요한 부분", content.issues.map((issue) => issue.message)),
    '<p class="note">창작자 AX에서 만든 초안이에요. AI 제안과 외부 사실은 따로 검토가 필요해요.</p>',
    "</body>",
    "</html>",
  ].join("\n");
}
