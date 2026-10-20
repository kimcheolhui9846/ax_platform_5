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

const FILE_FAILED = "문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.";

export const EXPORT_FAILED_NOTICE: Record<DocumentFormat, string> = {
  pdf: "인쇄 창을 열지 못했어요. 브라우저의 인쇄·팝업 차단을 확인하거나 Word·HTML로 받아 주세요.",
  docx: FILE_FAILED,
  html: FILE_FAILED,
};

export const EXPORT_BUSY_NOTICE = "문서를 만드는 중이에요. 끝난 뒤 다시 눌러 주세요.";

/** [순수] 파일로 받는 형식의 파일 이름. */
export function fileName(basename: string, format: "docx" | "html"): string {
  return `${basename}.${format}`;
}
