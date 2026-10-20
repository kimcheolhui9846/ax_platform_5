import { describe, expect, it } from "vitest";

import { DOCUMENT_FORMATS, EXPORTED_NOTICE, EXPORT_BUSY_NOTICE, EXPORT_FAILED_NOTICE, fileName } from "./documentFormats";

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
  });

  it("실패하면 형식에 맞게 경고하고, PDF는 인쇄 창이 막혔을 때 다른 형식을 권한다", () => {
    expect(EXPORT_FAILED_NOTICE).toEqual({
      pdf: "인쇄 창을 열지 못했어요. 브라우저의 인쇄·팝업 차단을 확인하거나 Word·HTML로 받아 주세요.",
      docx: "문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.",
      html: "문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.",
    });
  });

  it("만드는 중에 다시 누르면 기다리라고 경고한다", () => {
    expect(EXPORT_BUSY_NOTICE).toBe("문서를 만드는 중이에요. 끝난 뒤 다시 눌러 주세요.");
  });
});
