const SOURCE_LABEL: Record<string, string> = {
  user_free_text: "직접 입력",
  user_selected_ai_option: "선택",
  previous_task: "이전 과제",
  ai_assumption: "AI 가정",
  default: "기본값",
};

const CARD_LABEL: Record<string, string> = {
  diagnosis: "진단",
  suggestion: "제안",
  action: "실행 과제",
};

export function sourceLabel(source: string): string {
  return SOURCE_LABEL[source] ?? source;
}

export function cardLabel(cardType: string): string {
  return CARD_LABEL[cardType] ?? cardType;
}
