// 정보 출처 라벨은 백엔드가 SummaryItem.source_label로 보낸다(app/core/state.py의 SOURCE_LABELS 한곳).
const CARD_LABEL: Record<string, string> = {
  diagnosis: "진단",
  suggestion: "제안",
  action: "실행 과제",
};

export function cardLabel(cardType: string): string {
  return CARD_LABEL[cardType] ?? cardType;
}
