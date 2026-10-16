import type { screenOf } from "./screen";

export type NavKey = "home" | "work" | "documents";
export type Phase = 0 | 1 | 2;
export type ScreenKind = ReturnType<typeof screenOf>["kind"];
export type RailItem = { key: NavKey; label: string; active: boolean; disabled: boolean };

export const HEADER_STEPS = ["내 요청", "함께 구체화", "결과 만들기"] as const;

const NAV_LABELS: Record<NavKey, string> = { home: "홈", work: "내 작업", documents: "결과물" };
const NAV_ORDER: readonly NavKey[] = ["home", "work", "documents"];

/** 헤더의 3단계 표시. 과제 밖(null)에서는 단계를 보여 주지 않는다. */
export function headerSteps(phase: Phase | null): { label: string; current: boolean }[] {
  if (phase === null) return [];
  return HEADER_STEPS.map((label, i) => ({ label, current: i === phase }));
}

/** 화면 종류가 헤더의 몇 번째 단계인지. 과제를 고르기 전에는 과제 밖이다. */
export function phaseOf(kind: ScreenKind): Phase | null {
  if (kind === "pick_task") return null;
  if (kind === "idea") return 0;
  if (kind === "result") return 2;
  return 1;
}

const BUILT_NAV: ReadonlySet<NavKey> = new Set<NavKey>(["home"]);
const NO_NAV: ReadonlySet<NavKey> = new Set<NavKey>();

/** 지금 누를 수 있는 메뉴. 묶음 0에서는 홈만 만들었고, 요청 중에는 화면을 떠나지 못하게 모두 막는다. */
export function enabledNav(busy: boolean): ReadonlySet<NavKey> {
  return busy ? NO_NAV : BUILT_NAV;
}

/** 왼쪽 메뉴 항목. enabled에 없는 항목은 아직 만들지 않은 화면이라 막아 둔다. */
export function railItems(active: NavKey | null, enabled: ReadonlySet<NavKey>): RailItem[] {
  return NAV_ORDER.map((key) => ({
    key,
    label: NAV_LABELS[key],
    active: key === active,
    disabled: !enabled.has(key),
  }));
}
