# 결과 문서 내보내기(PDF·Word)와 예시 문구 교체 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 결과 문서를 PDF(브라우저 인쇄)·Word(.docx)·HTML로 내보내는 메뉴를 만들고, 요청 예시를 '한글 북백'으로 바꾼다.

**Architecture:** 화면은 형식과 상관없는 `DocumentFile { basename, content }`만 만든다(`documentFileOf`, 순수). 형식별 변환은 순수 함수(`documentHtml`, 새 `documentDocx`)가 하고, 부수 효과(파일 저장·인쇄)는 `lib/download.ts`의 `exportDocument(file, format)` 한 곳이다. App이 그것을 handlers에 넘긴다. 버튼은 `DownloadMenu` 하나.

**Tech Stack:** React 19, TypeScript, vitest(`renderToString`, DOM 없음), `docx`(9.x, dynamic import), 테스트용 `jszip`.

설계: `docs/superpowers/specs/2026-10-20-document-export-design.md`

## Global Constraints

- 비용 0: 서버·API 계약은 바꾸지 않는다(`gen:api` 불필요).
- HWP는 만들지 않는다.
- 메뉴 항목 문구: `PDF`, `Word(.docx)`, `HTML`. 버튼 문구: `문서 내려받기`.
- 알림: html·docx `문서를 내려받았어요.`, pdf `인쇄 창에서 ‘PDF로 저장’을 고르세요.`, 실패 `문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.`
- 파일 이름: `AX_{task_type}_V{n}.html` / `.docx`.
- `docx`는 첫 화면 번들에 넣지 않는다(`exportDocument` 안에서만 `import()`).
- CSS 색·글자 크기·폭·선·모서리는 `var(--…)`만(`tokens.test.ts`).
- 커밋 메시지에 AI 공동저자 표기를 넣지 않는다.
- 명령은 저장소 루트에서: `npm --prefix frontend test`, `npm --prefix frontend run build`, `uv run --directory backend pytest`.

---

### Task 1: 예시 문구를 한글 북백으로

**Files:**
- Modify: `backend/app/harness/tasks/business_plan/policy.yaml:6-8`
- Modify: `backend/app/harness/tasks/product_planning/policy.yaml:6-8,23`
- Modify: `backend/app/harness/tasks/branding/policy.yaml:6-8`
- Modify: `backend/app/harness/tasks/marketing_content/policy.yaml:6-8`
- Modify: `frontend/src/preview/fixtures.ts:48`
- Modify: `docs/DEMO.md:24`, `docs/HANDOFF.md`(스모크 예시 `"집들이 선물용 수제 향초"`)

- [ ] **Step 1:** 각 정책의 `input_placeholder`(앞에 `예) `)와 `input_examples` 첫 항목을 바꾼다(두 번째 예시는 그대로).
  - business_plan: `한글 디자인 북백을 온라인으로 팔고 싶어요`
  - product_planning: `외국인 관광객 선물용 한글 북백`
  - branding: `책 좋아하는 20대를 위한 한글 북백`
  - marketing_content: `한글날 한정 한글 북백을 알리고 싶어요`
- [ ] **Step 2:** product_planning 23행 `options: [향초·디퓨저, 액세서리, 문구·굿즈, 의류·패브릭]` → `options: [가방·패션잡화, 액세서리, 문구·굿즈, 의류·패브릭]`.
- [ ] **Step 3:** `fixtures.ts` `input_placeholder: "예) 외국인 관광객 선물용 한글 북백"`. DEMO.md 2번 입력과 HANDOFF 스모크 명령의 예시를 `외국인 관광객 선물용 한글 북백`으로.
- [ ] **Step 4:** `uv run --directory backend pytest -q` → 모두 통과. `npm --prefix frontend test` → 모두 통과.
- [ ] **Step 5:** 커밋 `요청 예시를 한글 북백으로`.

---

### Task 2: 형식 무관 `DocumentFile`, 형식 목록·알림, 인쇄 CSS

**Files:**
- Create: `frontend/src/lib/documentFormats.ts`, `frontend/src/lib/documentFormats.test.ts`
- Modify: `frontend/src/lib/document.ts`(타입 `DocumentFile` 추가)
- Modify: `frontend/src/lib/documentHtml.ts`(타입 제거, `STYLE`에 인쇄 규칙)
- Modify: `frontend/src/lib/documentHtml.test.ts`
- Modify: `frontend/src/app/documentFile.ts`, `frontend/src/app/documentFile.test.ts`
- Modify: `DocumentFile`을 `lib/documentHtml`에서 가져오던 곳(`app/handlers.ts`, `app/view.tsx`, `app/handlers.test.ts`, `lib/download.ts`) — import 경로만 `lib/document`로.

**Interfaces:**
- Produces:
  - `lib/document.ts`: `export type DocumentFile = { basename: string; content: DocumentContent & { request: string } };`
  - `lib/documentFormats.ts`: `DocumentFormat = "pdf" | "docx" | "html"`, `DOCUMENT_FORMATS: { format: DocumentFormat; label: string }[]`, `EXPORTED_NOTICE: Record<DocumentFormat, string>`, `EXPORT_FAILED_NOTICE: string`, `fileName(basename: string, format: "docx" | "html"): string`

- [ ] **Step 1: 실패하는 테스트**

`frontend/src/lib/documentFormats.test.ts`:
```ts
import { describe, expect, it } from "vitest";

import { DOCUMENT_FORMATS, EXPORTED_NOTICE, EXPORT_FAILED_NOTICE, fileName } from "./documentFormats";

describe("내보내기 형식", () => {
  it("메뉴는 PDF · Word · HTML 순서다", () => {
    expect(DOCUMENT_FORMATS).toEqual([
      { format: "pdf", label: "PDF" },
      { format: "docx", label: "Word(.docx)" },
      { format: "html", label: "HTML" },
    ]);
  });

  it("파일로 받는 형식은 확장자를 붙인다", () => {
    expect(fileName("AX_branding_V2", "docx")).toBe("AX_branding_V2.docx");
    expect(fileName("AX_branding_V2", "html")).toBe("AX_branding_V2.html");
  });

  it("PDF는 인쇄 창 안내, 나머지는 내려받음 알림", () => {
    expect(EXPORTED_NOTICE).toEqual({
      pdf: "인쇄 창에서 ‘PDF로 저장’을 고르세요.",
      docx: "문서를 내려받았어요.",
      html: "문서를 내려받았어요.",
    });
    expect(EXPORT_FAILED_NOTICE).toBe("문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.");
  });
});
```

`documentHtml.test.ts`에 추가:
```ts
  it("인쇄(PDF로 저장)해도 섹션이 중간에 끊기지 않게 인쇄 규칙을 담는다", () => {
    const html = documentHtml({ ...documentContent(makeTask(), makeResult(), false, {}), request: "r" });
    expect(html).toContain("@media print");
    expect(html).toContain("@page{margin:18mm}");
  });
```

`documentFile.test.ts`를 새 모양으로 바꾼다(`documentHtml`을 import해 내용 확인):
```ts
import { documentHtml } from "../lib/documentHtml";
// …
const html = (file: ReturnType<typeof documentFileOf>) => (file === null ? "" : documentHtml(file.content));
```
- 첫 테스트: `expect(file?.basename).toBe("AX_product_planning_V1")`, `expect(file?.content.request).toBe("한글 파우치")`, 저장 완료는 `.basename`이 `"AX_product_planning_V2"`.
- 나머지 `file?.html` 확인은 `html(file)`로, `file?.filename` 확인은 `file?.basename`(확장자 없이)로.

- [ ] **Step 2:** `npm --prefix frontend test` → documentFormats(모듈 없음)·documentHtml(인쇄 규칙)·documentFile(basename) 실패 확인.

- [ ] **Step 3: 구현**

`frontend/src/lib/documentFormats.ts`:
```ts
/** 결과 문서를 내보내는 형식. PDF는 브라우저 인쇄 창의 'PDF로 저장'으로 만든다. */
export type DocumentFormat = "pdf" | "docx" | "html";

export const DOCUMENT_FORMATS: { format: DocumentFormat; label: string }[] = [
  { format: "pdf", label: "PDF" },
  { format: "docx", label: "Word(.docx)" },
  { format: "html", label: "HTML" },
];

export const EXPORTED_NOTICE: Record<DocumentFormat, string> = {
  pdf: "인쇄 창에서 ‘PDF로 저장’을 고르세요.",
  docx: "문서를 내려받았어요.",
  html: "문서를 내려받았어요.",
};

export const EXPORT_FAILED_NOTICE = "문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.";

/** [순수] 파일로 받는 형식의 파일 이름. */
export function fileName(basename: string, format: "docx" | "html"): string {
  return `${basename}.${format}`;
}
```

`lib/document.ts` 끝(`DocumentContent` 뒤)에:
```ts
/** 내보낼 결과 문서. 형식(PDF·Word·HTML)과 상관없고, 확장자는 내보낼 때 형식이 붙인다. */
export type DocumentFile = { basename: string; content: DocumentContent & { request: string } };
```

`lib/documentHtml.ts`: `export type DocumentFile …` 줄을 지우고, `STYLE` 배열 끝에 한 줄 더한다:
```ts
  "@page{margin:18mm}@media print{body{margin:0;max-width:none}h2{break-after:avoid}figure,.record,tr{break-inside:avoid}a{color:inherit}}",
```

`app/documentFile.ts`:
```ts
import type { TaskSummary } from "../api/types";
import { documentContent } from "../lib/document";
import type { DocumentFile, Images, Shown } from "../lib/document";
import { versionIsStale } from "../lib/sessions";
import type { ScreenModel } from "./screenModel";

function fileFor(task: TaskSummary, request: string, shown: Shown, stale: boolean, images: Images): DocumentFile {
  return {
    basename: `AX_${task.task_type}_V${shown.version.version}`,
    content: { ...documentContent(task, shown, stale, images), request },
  };
}
```
(`documentFileOf`는 그대로.)

- [ ] **Step 4:** import 경로를 고친 뒤 `npm --prefix frontend test` → 새 테스트 통과. 이 단계에서는 `handlers.test.ts`의 다운로드 테스트와 `download.ts`가 옛 모양(`filename`·`html`)이라 타입이 어긋난다. `lib/download.ts`의 `saveFile`을 임시로 아래처럼 맞춘다(Task 4에서 교체):
```ts
import type { DocumentFile } from "./document";
import { documentHtml } from "./documentHtml";
import { fileName } from "./documentFormats";

export function saveFile({ basename, content }: DocumentFile): void {
  const url = URL.createObjectURL(new Blob([documentHtml(content)], { type: "text/html;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName(basename, "html");
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
```
`handlers.test.ts`의 다운로드 테스트 파일 값은 `{ basename: "AX_product_planning_V1", content: { ...documentContent(makeTask(), makeResult(), false, {}), request: "r" } }`로. `npm --prefix frontend test`와 `npm --prefix frontend run build` 통과.

- [ ] **Step 5:** 커밋 `내려받을 문서를 형식과 무관하게, 형식 목록·알림·인쇄 규칙`.

---

### Task 3: Word(.docx) 문서 만들기 `documentDocx`

**Files:**
- Modify: `frontend/package.json`(의존성 `docx`, 개발 의존성 `jszip`)
- Create: `frontend/src/lib/documentDocx.ts`, `frontend/src/lib/documentDocx.test.ts`

**Interfaces:**
- Consumes: `DocumentContent`, `DocumentFile["content"]`, `documentSections`(lib/document), `formatAssumption`, `PRIVATE_LABEL`
- Produces: `documentDocx(content: DocumentFile["content"]): Document`(docx), `imageOf(src: string | null): DocxImage | null`

- [ ] **Step 1:** `npm --prefix frontend install docx@9.13.0` 그리고 `npm --prefix frontend install -D jszip@3.10.2`.

- [ ] **Step 2: 실패하는 테스트** `frontend/src/lib/documentDocx.test.ts`:
```ts
import { Packer } from "docx";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import { makeResult, makeTask } from "../testing/factories";
import type { Images } from "./document";
import { documentContent } from "./document";
import { documentDocx, imageOf } from "./documentDocx";

// 1×1 PNG
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";

async function unpack(images: Images = {}, withImage = false) {
  const base = makeResult();
  const shown = withImage
    ? {
        ...base,
        result: {
          ...base.result,
          sections: [
            {
              order: 1,
              heading: "상품 콘셉트",
              kind: "diagnosis" as const,
              blocks: [
                { type: "text" as const, text: "첫 줄\n둘째 줄" },
                { type: "image" as const, asset_id: "a", alt: "참고 이미지", caption: "설명", origin: "ai_generated" as const },
              ],
            },
          ],
        },
      }
    : base;
  const content = { ...documentContent(makeTask(), shown, false, images), request: "북백 <b>굵게</b> & 끝" };
  const zip = await JSZip.loadAsync(await Packer.toBuffer(documentDocx(content)));
  return { xml: await zip.file("word/document.xml")!.async("string"), files: Object.keys(zip.files) };
}

describe("Word 문서(.docx)", () => {
  it("제목·위 줄·요청·기준·섹션을 담고 글자를 XML로 이스케이프한다", async () => {
    const { xml } = await unpack();
    expect(xml).toContain("상품기획 초안");
    expect(xml).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(xml).toContain("북백 &lt;b&gt;굵게&lt;/b&gt; &amp; 끝");
    expect(xml).toContain("상품 아이디어");
    expect(xml).toContain("상품 콘셉트");
    expect(xml).toContain("창작자 AX에서 만든 초안이에요.");
  });

  it("본문 줄바꿈은 줄 나눔으로 옮긴다", async () => {
    const { xml } = await unpack({}, true);
    expect(xml).toMatch(/첫 줄<\/w:t>.*<w:br\/>.*둘째 줄/s);
  });

  it("PNG 이미지는 문서에 넣는다", async () => {
    const { files, xml } = await unpack({ a: PNG }, true);
    expect(files.some((f) => f.startsWith("word/media/"))).toBe(true);
    expect(xml).toContain("설명");
  });

  it("넣을 수 없는 이미지(SVG·불러오지 못함)는 대체 글로 둔다", async () => {
    const { files, xml } = await unpack({ a: "data:image/svg+xml;base64,AA" }, true);
    expect(files.some((f) => f.startsWith("word/media/"))).toBe(false);
    expect(xml).toContain("[이미지: 참고 이미지]");
    expect((await unpack({ a: null }, true)).xml).toContain("[이미지: 참고 이미지]");
  });
});

describe("imageOf", () => {
  it("PNG는 머리에서 크기를 읽는다", () => {
    expect(imageOf(PNG)).toMatchObject({ type: "png", width: 1, height: 1 });
  });

  it("PNG·JPEG가 아니거나 비어 있으면 null", () => {
    expect(imageOf(null)).toBeNull();
    expect(imageOf("data:image/svg+xml;base64,AA")).toBeNull();
    expect(imageOf("data:image/png;base64,AAAA")).toBeNull();
  });
});
```
(`makeResult()`의 기준 행 라벨·섹션 제목은 `documentHtml.test.ts`가 쓰는 값과 같다: `상품 아이디어`, `상품 콘셉트`.)

- [ ] **Step 3:** `npm --prefix frontend test -- documentDocx` → 모듈 없음으로 실패.

- [ ] **Step 4: 구현** `frontend/src/lib/documentDocx.ts`:
```ts
import { Document, ExternalHyperlink, HeadingLevel, ImageRun, Paragraph, Table, TableCell, TableRow, TextRun, WidthType } from "docx";

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

/** 줄바꿈을 줄 나눔(w:br)으로 바꾼 글 조각. */
function runs(text: string, style: Style = {}): TextRun[] {
  return text.split("\n").map((line, index) => new TextRun({ text: line, ...style, ...(index > 0 ? { break: 1 } : {}) }));
}

function paragraph(text: string, style: Style = {}): Paragraph {
  return new Paragraph({ children: runs(text, style), spacing: { after: 120 } });
}

const note = (text: string) => paragraph(text, { color: MUTED, size: 18 });

function heading(text: string): Paragraph {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(text), spacing: { before: 360, after: 120 } });
}

function table(rows: [string, string][]): Table {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: rows.map(
      ([label, value]) =>
        new TableRow({
          children: [
            new TableCell({ width: { size: 25, type: WidthType.PERCENTAGE }, children: [paragraph(label, { bold: true })] }),
            new TableCell({ width: { size: 75, type: WidthType.PERCENTAGE }, children: [paragraph(value)] }),
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
  if (b.length < 24 || b[0] !== 0x89 || b[1] !== 0x50) return null;
  const view = new DataView(b.buffer, b.byteOffset);
  return [view.getUint32(16), view.getUint32(20)];
}

/** JPEG의 SOF 표지에서 크기를 읽는다. */
function jpegSize(b: Uint8Array): [number, number] | null {
  if (b.length < 4 || b[0] !== 0xff || b[1] !== 0xd8) return null;
  let i = 2;
  while (i + 9 < b.length) {
    if (b[i] !== 0xff) return null;
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
  if (block.kind === "text") return block.text.split(/\n{2,}/).map((part) => paragraph(part));
  const image = imageOf(block.src);
  if (image === null) return [note(`[이미지: ${block.alt}]`)];
  const picture = new Paragraph({
    children: [
      new ImageRun({
        type: image.type,
        data: image.data,
        transformation: { width: image.width, height: image.height },
        altText: { name: block.alt, title: block.alt, description: block.alt },
      }),
    ],
  });
  return block.caption ? [picture, note(block.caption)] : [picture];
}

function recordParagraphs(record: DocumentRecord): Paragraph[] {
  const source = record.url
    ? new ExternalHyperlink({ link: record.url, children: [new TextRun({ text: record.source, color: MUTED, size: 18, underline: {} })] })
    : new TextRun({ text: record.source, color: MUTED, size: 18 });
  const rest = record.note ? [new TextRun({ text: ` · ${record.note}`, color: MUTED, size: 18 })] : [];
  return [paragraph(record.label, { bold: true }), paragraph(record.text), new Paragraph({ children: [source, ...rest], spacing: { after: 240 } })];
}

const marks = (note: string | null, isPrivate: boolean) => `${note ? ` · ${note}` : ""}${isPrivate ? ` · ${PRIVATE_LABEL}` : ""}`;

/** [순수] 내려받을 결과 문서(Word). 내용·순서는 HTML 문서(documentHtml)와 같다. */
export function documentDocx(content: DocumentFile["content"]): Document {
  const sections = documentSections(content.result.sections, content.result.evidence, content.images).flatMap((s) => [
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 360, after: 120 },
      children: [new TextRun({ text: `${s.number} `, color: ACCENT }), new TextRun(s.heading), new TextRun({ text: ` ${s.tag}`, color: MUTED, size: 18 })],
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
    title: content.title,
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
```
(`CriteriaRow.note`는 `string | null`, `private`는 `boolean`, `AppliedRow`에는 `note`가 없다.)

- [ ] **Step 5:** `npm --prefix frontend test -- documentDocx` → 통과. 전체 `npm --prefix frontend test`와 `npm --prefix frontend run build` 통과.

- [ ] **Step 6:** 커밋 `Word(.docx) 결과 문서 만들기`.

---

### Task 4: `exportDocument`와 handlers 연결

**Files:**
- Modify: `frontend/src/lib/download.ts`
- Modify: `frontend/src/app/handlers.ts`, `frontend/src/app/handlers.test.ts`
- Modify: `frontend/src/app/view.tsx`(Handlers 타입과 `download` 헬퍼)
- Modify: `frontend/src/app/App.tsx`
- Modify: `frontend/src/preview/handlers.ts`(NOOP는 시그니처만 맞으면 그대로)

**Interfaces:**
- Consumes: `DocumentFile`, `DocumentFormat`, `EXPORTED_NOTICE`, `EXPORT_FAILED_NOTICE`, `fileName`, `documentHtml`, `documentDocx`
- Produces:
  - `lib/download.ts`: `exportDocument(file: DocumentFile, format: DocumentFormat): Promise<void>`
  - `Handlers.download: (file: DocumentFile, format: DocumentFormat) => void`
  - `makeHandlers` Deps: `exportDocument: (file: DocumentFile, format: DocumentFormat) => Promise<void>`(옛 `saveFile` 대신)
  - `renderScreen` 안의 `download: (format: DocumentFormat) => void` — 화면 부품의 `onDownload` 타입이 이것이 된다(Task 5).

- [ ] **Step 1: 실패하는 테스트** — `handlers.test.ts`:
  - `DOWNLOADED_NOTICE` import를 지우고 `import { EXPORTED_NOTICE, EXPORT_FAILED_NOTICE } from "../lib/documentFormats";`, `import type { DocumentFormat } from "../lib/documentFormats";`
  - `setup`에 `fail = false` 인자를 더한다: `function setup(patch: Partial<AppState> = {}, fail = false)`, `const exported: [DocumentFile, DocumentFormat][] = [];`, Deps에 `exportDocument: async (file, format) => { if (fail) throw new Error("x"); exported.push([file, format]); },`, 반환에 `exported`. (`saveFile`·`files`는 지운다.)
  - 다운로드 테스트를 바꾼다:
```ts
  const file = { basename: "AX_product_planning_V1", content: { ...documentContent(makeTask(), makeResult(), false, {}), request: "r" } };
  const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

  it("문서 내려받기는 고른 형식으로 내보내고 형식에 맞게 알린다", async () => {
    const { on, exported, actions } = setup();
    on.download(file, "docx");
    on.download(file, "pdf");
    await settle();
    expect(exported).toEqual([[file, "docx"], [file, "pdf"]]);
    expect(actions).toEqual([
      { type: "noticed", message: EXPORTED_NOTICE.docx },
      { type: "noticed", message: EXPORTED_NOTICE.pdf },
    ]);
  });

  it("문서를 만들지 못하면 실패를 알린다", async () => {
    const { on, actions } = setup({}, true);
    on.download(file, "docx");
    await settle();
    expect(actions).toEqual([{ type: "noticed", message: EXPORT_FAILED_NOTICE }]);
  });
```
  (`documentContent`, `makeTask`, `makeResult` import가 없으면 더한다.)

- [ ] **Step 2:** `npm --prefix frontend test -- handlers` → 실패 확인.

- [ ] **Step 3: 구현**

`lib/download.ts` 전체:
```ts
import type { DocumentFile } from "./document";
import type { DocumentFormat } from "./documentFormats";
import { fileName } from "./documentFormats";
import { documentHtml } from "./documentHtml";

const PRINT_CLEANUP_MS = 60_000; // afterprint가 오지 않는 브라우저에서 인쇄용 iframe을 지울 때까지

function saveBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** 보이지 않는 iframe에 문서를 넣고 인쇄 창을 연다('PDF로 저장'). 새 창이 아니라 팝업 차단에 걸리지 않는다. */
function printHtml(html: string): void {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.tabIndex = -1;
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  frame.addEventListener(
    "load",
    () => {
      const win = frame.contentWindow;
      if (win === null) return frame.remove();
      win.addEventListener("afterprint", () => frame.remove(), { once: true });
      window.setTimeout(() => frame.remove(), PRINT_CLEANUP_MS);
      win.focus();
      win.print();
    },
    { once: true },
  );
  frame.srcdoc = html;
  document.body.append(frame);
}

/** 결과 문서를 고른 형식으로 내보낸다. 화면 밖 부수 효과라 App이 handlers에 넘긴다(테스트는 가짜를 넘긴다). Word 라이브러리는 이때 불러온다. */
export async function exportDocument({ basename, content }: DocumentFile, format: DocumentFormat): Promise<void> {
  if (format === "pdf") return printHtml(documentHtml(content));
  if (format === "html") return saveBlob(fileName(basename, "html"), new Blob([documentHtml(content)], { type: "text/html;charset=utf-8" }));
  const [{ Packer }, { documentDocx }] = await Promise.all([import("docx"), import("./documentDocx")]);
  saveBlob(fileName(basename, "docx"), await Packer.toBlob(documentDocx(content)));
}
```

`app/handlers.ts`:
- `DOWNLOADED_NOTICE` 상수를 지운다(다른 곳에서 쓰면 `EXPORTED_NOTICE.html`로).
- import: `import type { DocumentFile } from "../lib/document";`, `import { EXPORTED_NOTICE, EXPORT_FAILED_NOTICE } from "../lib/documentFormats";`, `import type { DocumentFormat } from "../lib/documentFormats";`
- Deps: `saveFile: …` → `exportDocument: (file: DocumentFile, format: DocumentFormat) => Promise<void>;`, 구조 분해도 바꾼다.
- `download`:
```ts
    download: (file, format) => {
      exportDocument(file, format).then(
        () => dispatch({ type: "noticed", message: EXPORTED_NOTICE[format] }),
        () => dispatch({ type: "noticed", message: EXPORT_FAILED_NOTICE }),
      );
    },
```

`app/view.tsx`: Handlers 타입 `download: (file: DocumentFile, format: DocumentFormat) => void;`(import 경로 `../lib/document`, `../lib/documentFormats`), `renderScreen` 안:
```ts
  const download = (format: DocumentFormat) => {
    if (file) on.download(file, format);
  };
```
화면 부품의 `onDownload` prop 타입은 Task 5에서 바꾸므로, 이 단계에서는 세 화면(`ResultSide`·`SavedMain`·`VersionSide`)의 `onDownload` 타입을 `(format: DocumentFormat) => void`로 바꾸고 버튼은 임시로 `onClick={() => onDownload("html")}`로 둔다(동작은 지금과 같다).

`app/App.tsx`: `import { saveFile } from "../lib/download";` → `import { exportDocument } from "../lib/download";`, `makeHandlers({ … saveFile, })` → `exportDocument,`.

- [ ] **Step 4:** `npm --prefix frontend test`, `npm --prefix frontend run build` 통과. 빌드 출력에서 `docx`가 별도 청크(`dist/assets/…`)로 나뉘었는지 본다(첫 화면 `index-*.js` 크기가 크게 늘지 않아야 한다).

- [ ] **Step 5:** 커밋 `형식별 내보내기(PDF 인쇄·docx·HTML)와 알림`.

---

### Task 5: `DownloadMenu`와 세 화면, 미리보기 프레임

**Files:**
- Create: `frontend/src/components/DownloadMenu.tsx`
- Modify: `frontend/src/components/components.test.tsx`
- Modify: `frontend/src/screens/ResultScreen.tsx`, `SavedScreen.tsx`, `VersionScreen.tsx`
- Modify: `frontend/src/styles/screens.css`
- Modify: `frontend/src/preview/frames.tsx`, `frontend/src/preview/frames.test.tsx`
- Modify: `frontend/src/app/view.test.tsx`(내려받기 버튼 문구를 확인하는 곳이 있으면)

**Interfaces:**
- Consumes: `DOCUMENT_FORMATS`, `DocumentFormat`
- Produces: `DownloadMenu(props: { onDownload: (format: DocumentFormat) => void; disabled?: boolean; describedBy?: string; full?: boolean; initialOpen?: boolean })`

- [ ] **Step 1: 실패하는 테스트** — `components.test.tsx`에 import `import { DownloadMenu } from "./DownloadMenu";`와:
```tsx
describe("DownloadMenu", () => {
  it("닫혀 있으면 버튼만 있다", () => {
    const html = renderToString(<DownloadMenu onDownload={noop} />);
    expect(html).toContain("문서 내려받기");
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain("Word(.docx)");
  });

  it("열면 PDF · Word · HTML을 고를 수 있다", () => {
    const html = renderToString(<DownloadMenu initialOpen onDownload={noop} />);
    expect(html).toContain('aria-expanded="true"');
    expect(html.indexOf(">PDF<")).toBeLessThan(html.indexOf(">Word(.docx)<"));
    expect(html.indexOf(">Word(.docx)<")).toBeLessThan(html.indexOf(">HTML<"));
  });

  it("막혀 있으면 열린 상태여도 목록을 그리지 않고 안내를 잇는다", () => {
    const html = renderToString(<DownloadMenu initialOpen disabled describedBy="hint" onDownload={noop} />);
    expect(html).toContain("disabled");
    expect(html).toContain('aria-describedby="hint"');
    expect(html).not.toContain(">PDF<");
  });
});
```
`frames.test.tsx`의 프레임 id 목록에서 `"result-image",` 다음에 `"result-download",`를 더한다.

- [ ] **Step 2:** `npm --prefix frontend test` → DownloadMenu 없음, 프레임 목록 불일치로 실패.

- [ ] **Step 3: 구현** `frontend/src/components/DownloadMenu.tsx`:
```tsx
import { useId, useRef, useState } from "react";

import { DOCUMENT_FORMATS } from "../lib/documentFormats";
import type { DocumentFormat } from "../lib/documentFormats";

type Props = {
  onDownload: (format: DocumentFormat) => void;
  disabled?: boolean;
  describedBy?: string; // 막힌 이유 안내(최신 아님)
  full?: boolean; // 오른쪽 패널처럼 버튼을 한 줄 가득
  initialOpen?: boolean; // 미리보기 갤러리에서 연 상태를 그릴 때
};

/** '문서 내려받기' 버튼과 형식 목록(펼침). 열림은 이 부품 안에서 끝나는 UI 상태라 여기서 가진다. 고르거나 Esc로 닫으면 버튼으로 포커스를 돌려준다. */
export function DownloadMenu({ onDownload, disabled = false, describedBy, full = false, initialOpen = false }: Props) {
  const [open, setOpen] = useState(initialOpen);
  const opener = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const shown = open && !disabled;
  const buttonClass = full ? "btn full" : "btn";
  const close = () => {
    setOpen(false);
    opener.current?.focus();
  };
  return (
    <div
      className="download-menu stack8"
      onKeyDown={(event) => {
        if (event.key === "Escape" && shown) {
          event.stopPropagation();
          close();
        }
      }}
    >
      <button
        ref={opener}
        type="button"
        className={buttonClass}
        disabled={disabled}
        aria-expanded={shown}
        aria-controls={shown ? listId : undefined}
        aria-describedby={describedBy}
        onClick={() => setOpen(!open)}
      >
        문서 내려받기
      </button>
      {shown && (
        <ul id={listId} className="download-options stack8" aria-label="내려받을 형식">
          {DOCUMENT_FORMATS.map(({ format, label }) => (
            <li key={format}>
              <button
                type="button"
                className={buttonClass}
                onClick={() => {
                  close();
                  onDownload(format);
                }}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

`styles/screens.css` 끝에:
```css
/* 문서 내려받기 형식 목록 */
.download-options { list-style: none; margin: 0; padding: 0; }
```

화면 교체:
- `ResultScreen.tsx`: '문서 내려받기' `<button …>`을 `<DownloadMenu full disabled={busy || stale} describedBy={hinted} onDownload={onDownload} />`로.
- `SavedScreen.tsx`: 두 번째 `saved-actions` 안의 버튼을 `<DownloadMenu onDownload={onDownload} />`로.
- `VersionScreen.tsx`: `<DownloadMenu full onDownload={onDownload} />`로.
- 세 파일의 `onDownload` 타입은 `(format: DocumentFormat) => void`(Task 4에서 바꿈), 임시 `onClick={() => onDownload("html")}`은 사라진다.

`preview/frames.tsx`: import `DownloadMenu`, `"result-image"` 프레임 다음에:
```tsx
  dialogFrame(
    "result-download",
    "결과 · 문서 내려받기 형식 고르기",
    result,
    { kind: "result", task: PRODUCT, session: SESSION_DONE, result: RESULT, images: {} },
    () => <DownloadMenu full initialOpen onDownload={() => {}} />,
  ),
```

- [ ] **Step 4:** `npm --prefix frontend test`, `npm --prefix frontend run build` 통과. `view.test.tsx`에서 '문서 내려받기' 문구 확인이 깨지면 문구는 그대로이므로 마크업 차이만 맞춘다.

- [ ] **Step 5: 실제 확인** — `npm --prefix frontend run dev`와 백엔드(`uv run --directory backend python -m uvicorn app.main:app --port 8000`)를 띄워 결과까지 만든 뒤 메뉴에서 PDF(인쇄 창 열림)·Word(파일 받음, 열림)·HTML(파일 받음)을 확인한다. `/preview`의 `result-download` 프레임을 본다.

- [ ] **Step 6:** 커밋 `문서 내려받기 형식 메뉴(PDF·Word·HTML)`.

---

### Task 6: 문서·WBS·HANDOFF

**Files:**
- Modify: `CLAUDE.md`(구조: `frontend/src/app/` 설명의 내려받기 문장)
- Modify: `docs/HANDOFF.md`, `docs/WBS.xlsx`

- [ ] **Step 1:** `CLAUDE.md`의 "내려받는 문서는 `documentFile.ts`가 화면 모델에서 만들고(`lib/documentHtml.ts`, 이스케이프한 HTML 한 파일), 파일 저장(`lib/download.ts`)은 App이 handlers에 넘긴다." 를 다음으로 바꾼다: "내려받는 문서는 `documentFile.ts`가 화면 모델에서 형식과 무관하게(`DocumentFile`: 이름·내용) 만들고, 형식(`lib/documentFormats.ts`: PDF·Word·HTML)별 변환은 `lib/documentHtml.ts`(이스케이프한 HTML 한 파일, 인쇄 규칙 포함)·`lib/documentDocx.ts`(Word, `docx`는 내보낼 때만 불러온다)가 한다. 내보내기(`lib/download.ts`의 `exportDocument`: PDF는 숨은 iframe 인쇄 창, 나머지는 파일 저장)는 App이 handlers에 넘기고, 버튼은 `components/DownloadMenu`(형식 목록)다."
- [ ] **Step 2:** `uv run --no-project --with openpyxl python scripts/wbs.py list`로 행을 보고, `add`로 '결과 문서 내보내기(PDF·Word)·예시 문구 교체' 행을 더해 `완료`·완료일 2026-10-20·진척률 1·PR 번호를, `date`로 기준일을 오늘로.
- [ ] **Step 3:** HANDOFF: 기준일 2026-10-20, main·테스트 수(실제 실행 결과), "지금 상태" 표에 행(`#31 | 결과 문서 내보내기 | PDF(인쇄 창)·Word(.docx)·HTML 메뉴, 요청 예시 한글 북백`), 시연 확인 항목의 '보관은 문서 내려받기'는 그대로.
- [ ] **Step 4:** 백엔드·프론트 테스트·빌드 다시 통과 확인 후 커밋 `문서: 내보내기, WBS·HANDOFF`.
