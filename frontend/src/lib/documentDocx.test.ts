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
