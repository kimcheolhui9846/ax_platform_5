import { Packer } from "docx";
import JSZip from "jszip";
import { describe, expect, it } from "vitest";

import { documentFileOf } from "../app/documentFile";
import { documentDocx } from "../lib/documentDocx";
import { fileName } from "../lib/documentFormats";
import { documentHtml } from "../lib/documentHtml";
import { makeResult, makeSession, makeTask } from "../testing/factories";

const session = makeSession({ next_question: null, has_result: true, raw_input: "한글 파우치", name: "수제 향초 기획안" });
const shown = makeResult();
const file = documentFileOf({ kind: "result", task: makeTask(), session, result: shown, images: {} });

function exported() {
  if (file === null) throw new Error("결과 화면에서 문서가 만들어지지 않았다");
  return file;
}

describe("TC8 결과 내보내기", () => {
  it("TC8-3 결과 화면에서 내려받는 문서 이름은 '{작업 이름}_V{n}'이다", () => {
    expect(exported().basename).toBe("수제 향초 기획안_V1");
  });

  it("TC8-4 PDF로 여는 인쇄용 HTML에 제목·기준·섹션 본문·인쇄 규칙이 들어간다", () => {
    const html = documentHtml(exported().content);
    expect(html).toContain("상품기획 초안");
    expect(html).toContain(shown.summary[0].label);
    expect(html).toContain("집들이 선물용 수제 향초.");
    expect(html).toMatch(/@page|@media print/);
  });

  it("TC8-5 Word(.docx) 문서에도 같은 섹션 제목이 들어간다", async () => {
    const zip = await JSZip.loadAsync(await Packer.toBuffer(documentDocx(exported().content)));
    const xml = await zip.file("word/document.xml")!.async("string");
    expect(xml).toContain(shown.result.sections[0].heading);
    expect(xml).toContain("집들이 선물용 수제 향초.");
  });

  it("TC8-6 HTML 파일 이름 확장자는 형식을 따른다", () => {
    const name = exported().basename;
    expect(fileName(name, "html")).toBe("수제 향초 기획안_V1.html");
    expect(fileName(name, "docx")).toBe("수제 향초 기획안_V1.docx");
  });
});
