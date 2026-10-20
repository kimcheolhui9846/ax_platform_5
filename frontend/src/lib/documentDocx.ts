import { BorderStyle, Document, ExternalHyperlink, HeadingLevel, ImageRun, Paragraph, Table, TableCell, TableRow, TextRun, WidthType } from "docx";

import { formatAssumption } from "./assumption";
import type { DocumentBlock, DocumentFile, DocumentRecord } from "./document";
import { documentSections } from "./document";
import { PRIVATE_LABEL } from "./privacy";

// 내려받은 파일은 앱 밖에서 열리므로 색·글꼴을 파일 안에 둔다(HTML 문서와 같은 색).
const MUTED = "707070";
const ACCENT = "800122";
const FONT = "Malgun Gothic";
const MAX_IMAGE_WIDTH = 480; // 본문 폭에 맞춘 이미지 최대 폭(px)

type Style = { bold?: boolean; color?: string; size?: number };
export type DocxImage = { type: "png" | "jpg"; data: Uint8Array; width: number; height: number };

/** [순수] XML 1.0에 쓸 수 없는 제어 문자를 지운다(탭·줄바꿈은 남긴다). 남기면 Word가 파일을 열지 못한다. */
export const clean = (text: string) => text.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "");

/** 줄바꿈을 줄 나눔(w:br)으로 바꾼 글 조각. */
function runs(text: string, style: Style = {}): TextRun[] {
  return clean(text).split("\n").map((line, index) => new TextRun({ text: line, ...style, ...(index > 0 ? { break: 1 } : {}) }));
}

function paragraph(text: string, style: Style = {}): Paragraph {
  return new Paragraph({ children: runs(text, style), spacing: { after: 120 } });
}

const note = (text: string) => paragraph(text, { color: MUTED, size: 18 });

function heading(text: string): Paragraph {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(text), spacing: { before: 360, after: 120 } });
}

// HTML 표처럼 위에만 옅은 선을 긋는다.
const CELL_BORDERS = {
  top: { style: BorderStyle.SINGLE, size: 4, color: "E0E0E0" },
  bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
  right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
};

function table(rows: [string, string][]): Table {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: rows.map(
      ([label, value]) =>
        new TableRow({
          children: [
            new TableCell({ borders: CELL_BORDERS, width: { size: 25, type: WidthType.PERCENTAGE }, children: [paragraph(label, { bold: true })] }),
            new TableCell({ borders: CELL_BORDERS, width: { size: 75, type: WidthType.PERCENTAGE }, children: [paragraph(value)] }),
          ],
        }),
    ),
  });
}

function list(title: string, items: string[]): (Paragraph | Table)[] {
  if (items.length === 0) return [];
  return [heading(title), ...items.map((item) => new Paragraph({ children: runs(item), bullet: { level: 0 } }))];
}

function bytesOf(base64: string): Uint8Array | null {
  try {
    return Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
  } catch {
    return null;
  }
}

function pngSize(b: Uint8Array): [number, number] | null {
  const signature = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  const header = [0x49, 0x48, 0x44, 0x52]; // "IHDR"
  if (b.length < 24 || signature.some((v, i) => b[i] !== v) || header.some((v, i) => b[12 + i] !== v)) return null;
  const view = new DataView(b.buffer, b.byteOffset);
  return [view.getUint32(16), view.getUint32(20)];
}

/** JPEG의 SOF 표지에서 크기를 읽는다. */
function jpegSize(b: Uint8Array): [number, number] | null {
  if (b.length < 4 || b[0] !== 0xff || b[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 <= b.length) {
    if (b[i] !== 0xff) return null;
    while (b[i + 1] === 0xff) i++; // 표지 앞 채움 바이트
    const marker = b[i + 1];
    const length = (b[i + 2] << 8) | b[i + 3];
    if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
      return [(b[i + 7] << 8) | b[i + 8], (b[i + 5] << 8) | b[i + 6]];
    }
    i += 2 + length;
  }
  return null;
}

/** [순수] 문서에 넣을 수 있는 이미지(PNG·JPEG data URL, 크기를 읽을 수 있는 것). 아니면 null(대체 글). */
export function imageOf(src: string | null): DocxImage | null {
  const match = src?.match(/^data:image\/(png|jpeg);base64,(.+)$/);
  if (!match) return null;
  const data = bytesOf(match[2]);
  if (data === null) return null;
  const type = match[1] === "png" ? "png" : "jpg";
  const size = type === "png" ? pngSize(data) : jpegSize(data);
  if (size === null || size[0] === 0 || size[1] === 0) return null;
  const scale = Math.min(1, MAX_IMAGE_WIDTH / size[0]);
  return { type, data, width: Math.round(size[0] * scale), height: Math.round(size[1] * scale) };
}

function blockParagraphs(block: DocumentBlock): Paragraph[] {
  if (block.kind === "text") return clean(block.text).split(/\n{2,}/).map((part) => paragraph(part));
  const image = imageOf(block.src);
  if (image === null) return [note(`[이미지: ${block.alt}]`)];
  const picture = new Paragraph({
    children: [
      new ImageRun({
        type: image.type,
        data: image.data,
        transformation: { width: image.width, height: image.height },
        altText: { name: clean(block.alt), title: clean(block.alt), description: clean(block.alt) },
      }),
    ],
  });
  return block.caption ? [picture, note(block.caption)] : [picture];
}

function recordParagraphs(record: DocumentRecord): Paragraph[] {
  const source = record.url
    ? new ExternalHyperlink({ link: record.url, children: [new TextRun({ text: clean(record.source), color: MUTED, size: 18, underline: {} })] })
    : new TextRun({ text: clean(record.source), color: MUTED, size: 18 });
  const rest = record.note ? [new TextRun({ text: clean(` · ${record.note}`), color: MUTED, size: 18 })] : [];
  return [paragraph(record.label, { bold: true }), paragraph(record.text), new Paragraph({ children: [source, ...rest], spacing: { after: 240 } })];
}

const marks = (note: string | null, isPrivate: boolean) => `${note ? ` · ${note}` : ""}${isPrivate ? ` · ${PRIVATE_LABEL}` : ""}`;

/** [순수] 내려받을 결과 문서(Word). 내용·순서는 HTML 문서(documentHtml)와 같다. */
export function documentDocx(content: DocumentFile["content"]): Document {
  const sections = documentSections(content.result.sections, content.result.evidence, content.images).flatMap((s) => [
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 360, after: 120 },
      children: [new TextRun({ text: clean(`${s.number} `), color: ACCENT }), new TextRun(clean(s.heading)), new TextRun({ text: clean(` ${s.tag}`), color: MUTED, size: 18 })],
    }),
    ...s.blocks.flatMap(blockParagraphs),
    ...s.records.flatMap(recordParagraphs),
  ]);
  const supplements =
    content.supplements.length === 0
      ? []
      : [heading("보완 정보 · 사용자 입력 / 검증 전"), table(content.supplements.map((row) => [row.label, `${row.value}${marks("", row.private)}`]))];
  return new Document({
    creator: "창작자 AX",
    title: clean(content.title),
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    sections: [
      {
        children: [
          note(content.kicker),
          new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(content.title), spacing: { after: 240 } }),
          heading("내 요청"),
          paragraph(content.request),
          heading("내 답변에서 반영한 기준"),
          table(content.rows.map((row) => [row.label, `${row.value}${marks(row.note, row.private)}`])),
          ...sections,
          ...content.trailing.flatMap(recordParagraphs),
          ...supplements,
          ...list("AI가 가정한 내용", content.result.assumptions.map(formatAssumption)),
          ...list("검토가 필요한 부분", content.issues.map((issue) => issue.message)),
          note("창작자 AX에서 만든 초안이에요. AI 제안과 외부 사실은 따로 검토가 필요해요."),
        ],
      },
    ],
  });
}
