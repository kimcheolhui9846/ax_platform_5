import { AppShell } from "../layout/AppShell";
import type { RailProps } from "../layout/Rail";
import type { InventoryTab } from "../lib/routes";

type Props = {
  tab: InventoryTab;
  rail: RailProps;
  onTab: (tab: InventoryTab) => void;
};

/** 재고 화면(코칭과 상태를 섞지 않는다). 지금은 뼈대와 제목만 그린다. */
export function InventoryApp({ tab, rail, onTab }: Props) {
  void tab;
  void onTab;
  return (
    <AppShell
      rail={rail}
      header={{ project: "재고", phase: null, onPickTask: () => rail.onNavigate("home"), pickDisabled: rail.guideDisabled }}
    >
      <h1>재고</h1>
    </AppShell>
  );
}
