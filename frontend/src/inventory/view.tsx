import type { ItemKind } from "../api/types";
import { AppShell } from "../layout/AppShell";
import type { RailProps } from "../layout/Rail";
import { INVENTORY_TABS } from "../lib/routes";
import type { InventoryTab } from "../lib/routes";
import { CloseScreen } from "../screens/inventory/CloseScreen";
import type { CloseHandlers } from "../screens/inventory/CloseScreen";
import { ItemsScreen } from "../screens/inventory/ItemsScreen";
import type { ItemsHandlers } from "../screens/inventory/ItemsScreen";
import { StockScreen } from "../screens/inventory/StockScreen";
import type { CloseModel, ItemsModel, StockModel } from "./screenModel";
import type { InventoryCall } from "./state";

type Filter = { query: string; kind: ItemKind | "all" };

/**
 * 탭 화면이 그릴 모델. 탭 화면에 줄 데이터가 아직 없으면 loading, 불러오기에 실패하면 unavailable(다시 시도).
 * stock·close·items는 탭과 짝이다(`tab`이 다른 모델이 오면 안내만 그린다).
 */
export type InventoryScreenModel =
  | { kind: "loading" }
  | { kind: "unavailable" }
  | { kind: "stock"; model: StockModel; hasItems: boolean; filter: Filter }
  | { kind: "close"; model: CloseModel; filter: Filter }
  | { kind: "items"; model: ItemsModel };

/** 재고 화면이 부르는 모든 콜백(Task 7이 구현한다). 인자는 id·글·작은 값만. */
export type InventoryHandlers = CloseHandlers &
  ItemsHandlers & {
    onTab: (tab: InventoryTab) => void;
    /** 재고 화면 밖으로 가기 전(왼쪽 메뉴): 저장하지 않은 입력이 있으면 묻고, 떠나기로 하면 go를 부른다. */
    onLeave: (go: () => void) => void;
    onRetry: () => void;
  };

type ViewProps = {
  tab: InventoryTab;
  model: InventoryScreenModel;
  /** 지금 기다리는 요청의 종류(없으면 null). 눌린 버튼에 '저장 중…' 같은 글을 보인다. */
  busy: InventoryCall | null;
  on: InventoryHandlers;
  rail: RailProps;
  mainId?: string;
};

export const INVENTORY_TAB_LABELS: Record<InventoryTab, string> = { stock: "현황", close: "하루 마감", items: "품목·기준" };

/** 재고 화면 머리글 안내. */
export const INVENTORY_HINT = "하루 마감에 수량을 세면 부족한 재고를 알려 드려요.";

/** 문서 제목(코칭 화면의 pageTitle과 같은 모양). */
export function inventoryTitle(tab: InventoryTab): string {
  return `창작자 AX · 재고 ${INVENTORY_TAB_LABELS[tab]}`;
}

function TabBar({ tab, onTab }: { tab: InventoryTab; onTab: (tab: InventoryTab) => void }) {
  return (
    <nav className="inv-tabs" aria-label="재고 메뉴">
      {INVENTORY_TABS.map((t) => (
        <button key={t} type="button" className="inv-tab" aria-current={t === tab ? "page" : undefined} onClick={() => onTab(t)}>
          {INVENTORY_TAB_LABELS[t]}
        </button>
      ))}
    </nav>
  );
}

function TabScreen({ tab, model, busy, on }: Pick<ViewProps, "tab" | "model" | "busy" | "on">) {
  if (model.kind === "loading") return <p className="muted">불러오는 중이에요…</p>;
  if (model.kind === "unavailable") {
    return (
      <div className="notice stack">
        <p>재고를 불러오지 못했어요.</p>
        <button type="button" className="btn" onClick={on.onRetry}>
          다시 시도
        </button>
      </div>
    );
  }
  if (model.kind !== tab) return <p className="muted">불러오는 중이에요…</p>;
  if (model.kind === "stock") {
    return (
      <StockScreen
        model={model.model}
        hasItems={model.hasItems}
        filter={model.filter}
        onFilter={on.onFilter}
        onStartClose={() => on.onTab("close")}
        onOpenItems={() => on.onTab("items")}
      />
    );
  }
  if (model.kind === "close") {
    return (
      <CloseScreen
        model={model.model}
        filter={model.filter}
        busy={busy}
        on={{ ...on, onOpenStock: () => on.onTab("stock") }}
      />
    );
  }
  return <ItemsScreen model={model.model} busy={busy} on={on} />;
}

/** 재고 화면: 뼈대 + 탭 줄 + 탭 화면. */
export function InventoryView({ tab, model, busy, on, rail, mainId }: ViewProps) {
  return (
    <AppShell
      rail={rail}
      header={{ project: "재고", phase: null, hint: INVENTORY_HINT, onPickTask: () => rail.onNavigate("home"), pickDisabled: rail.guideDisabled }}
      mainId={mainId}
    >
      <TabBar tab={tab} onTab={on.onTab} />
      <TabScreen tab={tab} model={model} busy={busy} on={on} />
    </AppShell>
  );
}
