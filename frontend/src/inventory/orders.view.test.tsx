import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { InventoryView, ItemView } from "../api/types";
import { AutoOrderScreen } from "../screens/inventory/AutoOrderScreen";
import { OrderConfirm, OrderResultNotice } from "../screens/inventory/OrderConfirm";
import { OrderProposal } from "../screens/inventory/OrderProposal";
import { OrdersScreen } from "../screens/inventory/OrdersScreen";
import { autoModel, draftFromProposal, holdRows, orderCards, orderConfirmModel, orderProposals, orderResultText } from "./orderModel";
import { railProps } from "../app/view";
import { InventoryView as InventoryScreen } from "./view";
import type { OrderConfirmHandlers } from "../screens/inventory/OrderConfirm";
import type { InventoryHandlers } from "./view";

const noop = () => {};
const ON = new Proxy({}, { get: () => noop }) as InventoryHandlers;

const policy = { reorder_point: "5", target_stock: "20", unit_price: "4500", pack_size: "1" };
function item(id: string, name: string, over: Partial<ItemView> = {}): ItemView {
  return {
    item: { item_id: id, name, option: null, kind: "material", unit: "m", procurement: "purchase", supplier_id: "s-1", archived: false },
    on_hand: "2", in_transit: "0", status: "short", suggested_quantity: "18", policy, last_counted_at: null, suggestion: null, auto_order: null,
    ...over,
  } as unknown as ItemView;
}
function view(over: Record<string, unknown> = {}): InventoryView {
  return {
    items: [item("a", "원단")],
    suppliers: [{ supplier_id: "s-1", name: "한빛상사", mock_outcome: "accept" }],
    settings: { address: "서울시 어딘가", anomaly_drop_ratio: "0.5", stale_days: 7 },
    orders: [], holds: [], last_close: null,
    ...over,
  } as unknown as InventoryView;
}
const order = (over: Record<string, unknown> = {}) => ({
  order_id: "o-1", supplier_id: "s-1", origin: "manual", status: "accepted", created_at: "2026-11-08T01:00:00Z", total: "81000",
  lines: [{ item_id: "a", quantity: "18", received: "0" }, { item_id: "b", quantity: "4", received: "4" }], ...over,
});
const NO_ADDRESS = { address: "", anomaly_drop_ratio: "0.5", stale_days: 7 };

describe("OrderProposal", () => {
  it("제안이 없으면 그리지 않는다", () => {
    expect(renderToString(<OrderProposal groups={[]} busy={null} onOpen={noop} />)).toBe("");
  });
  it("거래처 카드마다 품목·제안량·단가와 주문 확인", () => {
    const html = renderToString(<OrderProposal groups={orderProposals(view())} busy={null} onOpen={noop} />);
    expect(html).toContain("부족한 구매 품목");
    expect(html).toContain("한빛상사");
    expect(html).toContain("원단");
    expect(html).toContain("주문 확인");
    expect(html).toMatch(/<button[^>]*aria-label="한빛상사 주문 확인"/); // 거래처마다 구분되는 이름
    expect(html).not.toMatch(/<button[^>]*disabled/);
  });
  it("요청 중이면 막는다", () => {
    expect(renderToString(<OrderProposal groups={orderProposals(view())} busy="save" onOpen={noop} />)).toMatch(/<button[^>]*disabled=""[^>]*>주문 확인/);
  });
});

describe("OrderConfirm", () => {
  const v = view();
  const group = orderProposals(v)[0];
  const draw = (model: ReturnType<typeof orderConfirmModel>, busy: "order" | "save" | null = null) =>
    renderToString(<OrderConfirm model={model} busy={busy} on={ON as unknown as OrderConfirmHandlers} />);
  it("제목·수량 입력 이름·예상 총액·주문하기", () => {
    const html = draw(orderConfirmModel(v, draftFromProposal(group, "manual:1")));
    expect(html).toContain("주문 확인: 한빛상사");
    expect(html).toMatch(/<input[^>]*aria-label="원단 주문 수량\(m\)"[^>]*value="18"/);
    expect(html).toContain("예상 총액");
    expect(html).toContain("실제 금액은 주문 뒤 확인");
    expect(html).toContain("빼기");
    expect(html).toContain("취소");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>주문하기/);
    expect(html).not.toContain("새 단가로 주문해요");
  });
  it("수량이 올바르지 않으면 주문하기가 막힌다", () => {
    const d = draftFromProposal(group, "manual:1");
    const html = draw(orderConfirmModel(v, { ...d, lines: [{ ...d.lines[0], quantity: "0" }] }));
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>주문하기/);
  });
  it("배송지가 없으면 경고와 품목·기준으로 가는 버튼, 주문하기 막힘", () => {
    const html = draw(orderConfirmModel(view({ settings: NO_ADDRESS }), draftFromProposal(group, "manual:1")));
    expect(html).toContain("배송지를 먼저 설정해 주세요");
    expect(html).toContain("품목·기준으로 가기");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>주문하기/);
  });
  it("새 단가 초안은 안내를 보인다", () => {
    const d = { ...draftFromProposal(group, "manual:1"), repriced: true };
    expect(draw(orderConfirmModel(v, d))).toContain("거래처가 알려 준 새 단가로 주문해요");
  });
  it("주문 중이면 진행 글과 막힘", () => {
    const html = draw(orderConfirmModel(v, draftFromProposal(group, "manual:1")), "order");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>주문 중…/);
    expect(html).toMatch(/<input[^>]*aria-label="원단 주문 수량\(m\)"[^>]*disabled=""/);
  });
  it("다른 종류의 요청 중에도 주문하기가 막힌다", () => {
    expect(draw(orderConfirmModel(v, draftFromProposal(group, "manual:1")), "save")).toMatch(/<button[^>]*disabled=""[^>]*>주문하기/);
  });
});

describe("OrderResultNotice", () => {
  it("결과 문구 3종이 role=status 안에 보이고 버튼이 둘", () => {
    for (const [notice, text] of [
      [{ status: "accepted", holdReason: null }, "주문이 접수됐어요"],
      [{ status: "rejected", holdReason: "out_of_stock" }, "주문이 거절됐어요: "],
      [{ status: "unknown", holdReason: null }, "접수 여부를 확인하지 못했어요"],
    ] as const) {
      const html = renderToString(<OrderResultNotice text={orderResultText(notice)} onOpenOrders={noop} onClose={noop} />);
      expect(html).toMatch(/role="status"/);
      expect(html).toContain(text);
      expect(html).toContain("주문·입고 보기");
      expect(html).toContain("닫기");
    }
  });
});

describe("OrdersScreen", () => {
  const draw = (v: InventoryView, busy: "refresh" | "resolve" | "save" | null = null) =>
    renderToString(<OrdersScreen orders={orderCards(v)} holds={holdRows(v)} saved={0} busy={busy} on={ON} />);
  it("비어 있으면 안내 두 가지", () => {
    const html = draw(view());
    expect(html).toContain("보류된 일이 없어요");
    expect(html).toContain("주문이 없어요");
  });
  it("보류 줄: 사유·새 단가와 버튼 조건", () => {
    const v = view({
      items: [item("a", "원단"), item("c", "단추", { suggested_quantity: null })],
      holds: [
        { hold_id: "h-1", item_id: "a", order_id: null, reason: "price_changed", current_unit_price: "5000", created_at: "2026-11-08T01:00:00Z", resolved: false },
        { hold_id: "h-2", item_id: "c", order_id: "o-u", reason: "unknown_result", current_unit_price: null, created_at: "2026-11-08T01:00:00Z", resolved: false },
      ],
      orders: [order({ order_id: "o-u", status: "unknown" })],
    });
    const html = draw(v);
    expect(html.match(/새 단가로 다시 주문/g)?.length).toBe(1);
    expect(html).toContain("5,000");
    expect(html.match(/해결로 표시/g)?.length).toBe(2);
    expect(html.match(/다시 확인/g)?.length).toBeGreaterThanOrEqual(2); // 보류 줄 + 주문 카드
  });
  it("보류 뒤에 다시 주문했으면 다시 주문 버튼 대신 해결 안내", () => {
    const v = view({
      items: [item("a", "원단"), item("b", "실")],
      holds: [{ hold_id: "h-1", item_id: "a", order_id: null, reason: "price_changed", current_unit_price: "5000", created_at: "2026-11-08T01:00:00Z", resolved: false }],
      orders: [order({ created_at: "2026-11-08T02:00:00Z" })],
    });
    const html = draw(v);
    expect(html).not.toMatch(/>\s*새 단가로 다시 주문\s*</); // 버튼 없음
    expect(html).toContain("새 단가로 다시 주문했어요");
  });
  it("주문 카드: 접수 주문은 입고 양식(남은 0 줄 제외), 재조회 없음", () => {
    const html = draw(view({ items: [item("a", "원단"), item("b", "실")], orders: [order()] }));
    expect(html).toContain("한빛상사");
    expect(html).toContain("입고 저장");
    expect(html).toContain("이미 마감에서 셌어요");
    expect(html).toMatch(/<input type="checkbox"[^>]*aria-label="원단 이미 마감에서 셌어요"/); // 줄마다 구분되는 이름
    expect(html).toMatch(/aria-label="원단 입고 수량\(m\)"[^>]*value="18"/);
    expect(html).not.toMatch(/aria-label="실 입고 수량/);
    expect(html).not.toContain("다시 확인");
  });
  it("접수 불명 주문은 재조회만, 입고 양식 없음. 요청 중엔 확인 중", () => {
    const v = view({ orders: [order({ status: "unknown" })] });
    expect(draw(v)).toContain("다시 확인");
    expect(draw(v)).not.toContain("입고 저장");
    expect(draw(v, "refresh")).toContain("확인 중…");
  });
  it("입고 양식은 요청 중 막힌다", () => {
    expect(draw(view({ orders: [order()] }), "save")).toMatch(/<button[^>]*disabled=""[^>]*>저장 중…/);
  });
});

describe("AutoOrderScreen", () => {
  const draw = (v: InventoryView, busy: "save" | null = null) =>
    renderToString(<AutoOrderScreen model={autoModel(v)} items={v.items} saved={0} busy={busy} on={ON} initialSelected="a" />);
  it("배송지가 없으면 경고", () => {
    expect(draw(view({ settings: NO_ADDRESS }))).toContain("배송지를 먼저 설정해 주세요");
    expect(draw(view())).not.toContain("배송지를 먼저 설정해 주세요");
  });
  it("표에 최근 결과, 주문 불가면 선택이 막히고 사유", () => {
    const html = draw(view({ items: [item("a", "원단"), item("n", "끈", { policy: null })] }));
    expect(html).toMatch(/<button[^>]*aria-label="원단 선택"/); // 품목마다 구분되는 이름
    expect(html).toContain("아직 없음");
    expect(html).toContain("거래처와 보충 기준이 필요해요");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>선택/);
  });
  it("편집 카드: 처음 값, 꺼짐이면 동의 칸 없음", () => {
    const html = draw(view());
    expect(html).toContain("자동 주문 켜기");
    const field = (label: string) => {
      const id = html.match(new RegExp(`<label for="([^"]+)">${label.replace(/[()]/g, "\\$&")}</label>`))?.[1];
      return id === undefined ? "" : (html.match(new RegExp(`<input[^>]*id="${id}"[^>]*>`))?.[0] ?? "");
    };
    expect(field("1회 한도(원)")).toContain('value="100000"'); // 보이는 이름표가 입력칸과 이어진다
    expect(field("월 한도(원)")).toContain('value="300000"');
    expect(html).not.toContain("하루 마감 직후 이 한도 안에서");
  });
  it("켜진 설정이면 동의 칸이 보이고, 동의 기록이 없으면 저장이 막힌다", () => {
    const setting = { enabled: true, consented_at: null, per_order_limit: "1000", monthly_limit: "5000" };
    const html = draw(view({ items: [item("a", "원단", { auto_order: setting })] }));
    expect(html).toContain("부족할 때 하루 마감 직후 이 한도 안에서 자동으로 주문하는 데 동의해요");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>저장/);
    const consented = { ...setting, consented_at: "2026-11-01T00:00:00Z" };
    expect(draw(view({ items: [item("a", "원단", { auto_order: consented })] }))).not.toMatch(/<button[^>]*disabled=""[^>]*>저장/);
  });
});

describe("InventoryView의 주문 패널", () => {
  const rail = railProps({ name: "inventory", tab: "items" }, false, new Proxy({}, { get: () => noop }) as never);
  it("확인 카드와 결과 안내는 어느 탭에서나 탭 줄 아래에 뜬다", () => {
    const v = view();
    const confirm = orderConfirmModel(v, draftFromProposal(orderProposals(v)[0], "manual:1"));
    const html = renderToString(
      <InventoryScreen tab="items" model={{ kind: "loading" }} panel={{ confirm, result: "주문이 접수됐어요" }} busy={null} on={ON} rail={rail} />,
    );
    expect(html).toContain("주문 확인: 한빛상사");
    expect(html).toContain("주문이 접수됐어요");
    expect(html.indexOf("재고 메뉴")).toBeLessThan(html.indexOf("주문 확인: 한빛상사"));
  });
  it("주문 탭과 자동 주문 탭을 그린다", () => {
    const v = view();
    const orders = renderToString(
      <InventoryScreen tab="orders" model={{ kind: "orders", orders: orderCards(v), holds: holdRows(v), saved: 0 }} panel={{ confirm: null, result: null }} busy={null} on={ON} rail={rail} />,
    );
    expect(orders).toContain("주문이 없어요");
    const auto = renderToString(
      <InventoryScreen tab="auto" model={{ kind: "auto", model: autoModel(v), items: v.items, saved: 0 }} panel={{ confirm: null, result: null }} busy={null} on={ON} rail={rail} />,
    );
    expect(auto).toContain("자동 주문");
  });
});
