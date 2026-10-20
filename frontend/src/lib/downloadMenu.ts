/** 내려받기 메뉴에 일어난 일. disabled는 버튼이 막혔다는 신호다. */
export type MenuEvent = "toggle" | "choose" | "escape" | "blur" | "disabled";

/** [순수] 메뉴가 열려 있어야 하는지. 버튼은 뒤집고, 나머지는 모두 닫는다(막힌 채 열림이 남아 풀릴 때 다시 열리지 않게). */
export function menuAfter(open: boolean, event: MenuEvent): boolean {
  return event === "toggle" ? !open : false;
}
