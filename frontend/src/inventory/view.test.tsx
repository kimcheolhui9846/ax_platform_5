import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { CloseCheckView, InventoryView, ItemView } from "../api/types";
import { railProps } from "../app/view";
import { closeModel, itemsModel, stockModel } from "./screenModel";
import { EMPTY_CLOSE, initialInventoryState } from "./state";
import { InventoryView as InventoryScreen, inventoryTitle } from "./view";
import type { InventoryHandlers, InventoryScreenModel } from "./view";
import { INVENTORY_HINT } from "./view";
import { CloseScreen } from "../screens/inventory/CloseScreen";
import { ItemsScreen } from "../screens/inventory/ItemsScreen";
import { StockScreen } from "../screens/inventory/StockScreen";
import { ItemEditForm, PolicyForm } from "../screens/inventory/ItemForms";

const noop = () => {};
const NO_SAVES = initialInventoryState().saved;
const ON = new Proxy({}, { get: () => noop }) as InventoryHandlers;
const FILTER = { query: "", kind: "all" as const };

function item(id: string, name: string, over: Partial<ItemView> = {}): ItemView {
  return {
    item: { item_id: id, name, option: null, kind: "material", unit: "m", procurement: "purchase", supplier_id: null, archived: false },
    on_hand: "10", in_transit: "0", status: "ok", suggested_quantity: null, policy: null, last_counted_at: null, suggestion: null, auto_order: null,
    ...over,
  };
}
function view(items: ItemView[]): InventoryView {
  return { items, suppliers: [], settings: { address: "", anomaly_drop_ratio: "0.5", stale_days: 7 }, last_close: null } as unknown as InventoryView;
}

describe("StockScreen", () => {
  it("미입력은 0이 아니라 '미입력'으로 보인다", () => {
    const v = view([item("a", "원단", { on_hand: null, status: "uncounted" })]);
    const html = renderToString(<StockScreen model={stockModel(v, FILTER)} hasItems filter={FILTER} onFilter={noop} onStartClose={noop} onOpenItems={noop} />);
    expect(html).toContain("미입력 1개");
    expect(html).toContain("미입력");
    expect(html).toContain(`data-label="보유" class="num">미입력`);
    expect(html).toContain("하루 마감 하기");
  });
  it("품목이 없으면 품목·기준으로 가는 빈 화면", () => {
    const html = renderToString(<StockScreen model={stockModel(view([]), FILTER)} hasItems={false} filter={FILTER} onFilter={noop} onStartClose={noop} onOpenItems={noop} />);
    expect(html).toContain("등록한 품목이 없어요");
    expect(html).toContain("품목·기준으로 가기");
  });
});

describe("CloseScreen", () => {
  const v = view([item("a", "원단")]);
  const draw = (counts: Record<string, string>, check: CloseCheckView | null, busy: "check" | "close" | null = null, extra = {}) =>
    renderToString(
      <CloseScreen
        model={closeModel(v, { ...EMPTY_CLOSE, date: "2026-11-08", counts, check, ...extra }, FILTER)}
        filter={FILTER}
        busy={busy}
        on={ON}
      />,
    );
  it("미입력 안내와 지난 수량, 검사 전에는 마감 저장이 막힌다", () => {
    const html = draw({ a: "5" }, null);
    expect(html).toContain("비워 두면 미입력으로 남아요(0이 아니에요)");
    expect(html).toContain("지난 수량 10 m");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>마감 저장/);
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>검사/);
  });
  it("수량 칸의 보이는 이름표는 품목 이름과 지난 수량 하나이고, 입력 이름은 '실사 수량'", () => {
    const html = draw({}, null);
    const label = html.match(/<label[^>]*for="([^"]*-count-a)"[^>]*>(.*?)<\/label>/);
    expect(label?.[2]).toContain("원단");
    expect(label?.[2]).toContain("지난 수량 10 m");
    expect(html).toMatch(/<input[^>]*aria-label="원단 실사 수량\(m\)"/);
    expect(html.match(/<label[^>]*for="[^"]*-count-/g)?.length).toBe(html.match(/<input[^>]*id="[^"]*-count-/g)?.length); // 수량 칸마다 이름표 하나
  });
  it("요청 중엔 입력과 버튼이 막히고 눌린 버튼에 진행 글", () => {
    const html = draw({ a: "5" }, null, "check");
    expect(html).toContain("검사 중…");
    expect(html).toMatch(/<input[^>]*id="[^"]*-count-a"[^>]*disabled=""/);
  });
  it("조정 사유가 없으면 확인이 막힌다", () => {
    const check = { anomalies: [{ item_id: "a", kind: "drop", previous: "10", counted: "1" }] } as unknown as CloseCheckView;
    const html = draw({ a: "1" }, check, null, { adjustments: { a: { delta: "2", reason: "" } } });
    expect(html).toContain("조정에는 사유가 꼭 필요해요");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>맞아요/);
  });
  it("마감 결과 패널은 서버가 저장한 날짜를 보인다", () => {
    const html = draw({}, null, null, {
      result: { close: { close_date: "2026-11-06" }, auto_orders: [], inventory: v },
    });
    expect(html).toContain("저장한 날짜: 2026-11-06");
    expect(html).toContain("자동 주문 없음");
    expect(html).toContain("재고 현황 보기");
  });
});

describe("ItemsScreen·품목 양식", () => {
  const suggested = item("a", "원단", {
    last_counted_at: "2026-11-01T00:00:00Z",
    suggestion: { min_stock: "5", target_stock: "20", purchase_unit: "5", reason: "최근 사용량 기준" },
  } as Partial<ItemView>);
  const row = itemsModel(view([suggested]), NO_SAVES).rows[0];
  const policy = (busy: "suggest" | "save" | null) =>
    renderToString(<PolicyForm item={row} busy={busy} onSave={noop} onSuggest={noop} onApply={noop} onEdited={noop} />);
  it("추천은 '확인 전'과 이유, 적용 버튼으로 보인다", () => {
    const html = policy(null);
    expect(html).toContain("확인 전");
    expect(html).toContain("최근 사용량 기준");
    expect(html).toContain("추천 적용");
    expect(html).toContain("AI 추천 받기");
  });
  it("추천을 받는 중엔 '추천 받는 중…'이고 입력과 버튼이 모두 막힌다", () => {
    const html = policy("suggest");
    expect(html).toContain("추천 받는 중…");
    expect(html).not.toMatch(/<(input|button)(?![^>]*disabled)[^>]*>/);
  });
  it("저장한 보충 기준이 없으면 추천 버튼을 막고 먼저 저장하라고 안내한다", () => {
    const suggestButton = (r: typeof row) =>
      renderToString(<PolicyForm item={r} busy={null} onSave={noop} onSuggest={noop} onApply={noop} onEdited={noop} />).match(/<button[^>]*>AI 추천 받기<\/button>/)?.[0] ?? "";
    const saved = { ...row, policy: { min_stock: "5", target_stock: "20", purchase_unit: "5", lead_days: 2, unit_price: "1000" } };
    expect(suggestButton({ ...row, policy: null })).toContain("disabled");
    expect(renderToString(<PolicyForm item={{ ...row, policy: null }} busy={null} onSave={noop} onSuggest={noop} onApply={noop} onEdited={noop} />)).toContain("보충 기준을 저장하면 AI 추천을 받을 수 있어요");
    expect(suggestButton(saved)).not.toContain("disabled");
  });
  it("저장 중엔 '저장 중…'", () => {
    expect(policy("save")).toContain("저장 중…");
  });
  it("단위 잠금 안내는 수량 기록이 있는 품목에만", () => {
    const edit = (r: typeof row) => renderToString(<ItemEditForm item={r} suppliers={[]} busy={null} onSave={noop} onEdited={noop} />);
    expect(edit(row)).toContain("단위를 바꿀 수 없어요");
    expect(edit({ ...row, counted: false })).not.toContain("단위를 바꿀 수 없어요");
  });
  it("수량 기록이 있는 품목은 단위 입력을 막는다", () => {
    const edit = (r: typeof row) => renderToString(<ItemEditForm item={r} suppliers={[]} busy={null} onSave={noop} onEdited={noop} />);
    const unit = (html: string) => html.match(/<input[^>]*id="[^"]*-edit-unit"[^>]*>/)?.[0] ?? "";
    expect(unit(edit(row))).toContain("disabled");
    expect(unit(edit({ ...row, counted: false }))).not.toContain("disabled");
  });
  it("품목 탭은 요청 중이면 입력과 버튼을 막는다", () => {
    const html = renderToString(<ItemsScreen model={itemsModel(view([suggested]), NO_SAVES)} busy="save" on={ON} />);
    expect(html).toContain("저장 중…");
    expect(html).not.toMatch(/<(input|button|select)(?![^>]*disabled)[^>]*>/);
  });
});

describe("InventoryView", () => {
  const rail = railProps({ name: "inventory", tab: "stock" }, false, { navigate: vi.fn(), guide: vi.fn() });
  const draw = (tab: "stock" | "close" | "items", model: InventoryScreenModel) =>
    renderToString(<InventoryScreen tab={tab} model={model} busy={null} on={ON} rail={rail} />);
  it("탭 줄에 현재 탭 aria-current", () => {
    const html = draw("close", { kind: "loading" });
    expect(html).toMatch(/aria-current="page"[^>]*>하루 마감/);
    expect(html).toContain("불러오는 중이에요");
  });
  it("불러오지 못하면 다시 시도", () => {
    expect(draw("stock", { kind: "unavailable" })).toContain("다시 시도");
  });
  it("머리글은 재고 안내를 보이고 코칭 안내는 보이지 않는다", () => {
    const html = draw("stock", { kind: "loading" });
    expect(html).toContain(INVENTORY_HINT);
    expect(html).not.toContain("하고 싶은 작업 하나부터 시작하세요.");
  });
  it("문서 제목은 탭 이름을 담는다", () => {
    expect(inventoryTitle("close")).toBe("창작자 AX · 재고 하루 마감");
    expect(inventoryTitle("stock")).toBe("창작자 AX · 재고 현황");
  });
  it("품목·기준 탭", () => {
    expect(draw("items", { kind: "items", model: itemsModel(view([]), NO_SAVES) })).toContain("품목 일괄 등록");
  });
});
