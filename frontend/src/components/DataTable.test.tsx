import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DataTable } from "./DataTable";

type Row = { id: string; name: string; qty: string };
const rows: Row[] = [
  { id: "a", name: "원두", qty: "12" },
  { id: "b", name: "우유", qty: "3" },
];
const columns = [
  { key: "name", header: "품목", cell: (r: Row) => r.name },
  { key: "qty", header: "수량", cell: (r: Row) => r.qty, align: "end" as const },
];
const html = (data: Row[]) =>
  renderToString(<DataTable caption="재고 목록" columns={columns} rows={data} rowKey={(r) => r.id} empty="품목이 없어요." />);

describe("DataTable", () => {
  it("머리글·셀·caption을 그린다", () => {
    const out = html(rows);
    expect(out).toContain("<caption");
    expect(out).toContain("재고 목록");
    expect(out).toContain("품목</th>");
    expect(out).toContain("원두");
    expect(out).toContain("우유");
  });

  it("셀마다 머리글을 data-label로 단다", () => {
    const out = html(rows);
    expect(out).toContain('data-label="품목"');
    expect(out).toContain('data-label="수량"');
  });

  it("끝 정렬 열은 num 클래스를 가진다", () => {
    expect(html(rows)).toMatch(/<td[^>]*class="num"[^>]*>12/);
  });

  it("행이 없으면 빈 문장만 보인다", () => {
    const out = html([]);
    expect(out).toContain("품목이 없어요.");
    expect(out).not.toContain("<table");
  });
});
