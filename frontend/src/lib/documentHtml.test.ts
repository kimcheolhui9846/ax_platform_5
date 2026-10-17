import { describe, expect, it } from "vitest";

import { makeResult, makeTask } from "../testing/factories";
import { documentContent } from "./document";
import { documentHtml, escapeHtml } from "./documentHtml";

describe("내려받을 문서(HTML)", () => {
  it("글자를 이스케이프한다", () => {
    expect(escapeHtml(`<script>alert("x")</script> & '`)).toBe("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &#39;");
  });

  it("제목·위 줄·요청·기준·섹션을 담은 한 파일이다", () => {
    const content = documentContent(makeTask(), makeResult(), false);
    const html = documentHtml({ ...content, request: "수제 향초 <b>굵게</b>" });
    expect(html.startsWith("<!doctype html>")).toBe(true);
    expect(html).toContain('<meta charset="utf-8">');
    expect(html).toContain("<title>상품기획 초안</title>");
    expect(html).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(html).toContain("수제 향초 &lt;b&gt;굵게&lt;/b&gt;");
    expect(html).toContain("<th>상품 아이디어</th>");
    expect(html).toContain('<span class="num">01</span> 상품 콘셉트');
  });

  it("보완 정보는 사용자 입력 · 검증 전으로 싣고, 없으면 칸을 두지 않는다", () => {
    const base = { ...documentContent(makeTask(), makeResult(), false), request: "향초" };
    expect(documentHtml(base)).not.toContain("보완 정보");
    const html = documentHtml({ ...base, supplements: [{ label: "소재", value: "<면>" }] });
    expect(html).toContain("<h2>보완 정보 · 사용자 입력 / 검증 전</h2>");
    expect(html).toContain("<tr><th>소재</th><td>&lt;면&gt;</td></tr>");
  });

  it("AI 가정과 검토 항목은 있을 때만 넣는다", () => {
    const plain = documentHtml({ ...documentContent(makeTask(), makeResult(), false), request: "x" });
    expect(plain).not.toContain("AI가 가정한 내용");
    expect(plain).not.toContain("검토가 필요한 부분");

    const shown = makeResult({ validation: { issues: [{ rule: "r", message: "근거를 확인해 주세요.", severity: "warning" }], passed: true } });
    shown.result.assumptions = [{ field: "price", label: "가격 방향", value: "1~3만원", reason: "", requires_confirmation: true }];
    const rich = documentHtml({ ...documentContent(makeTask(), shown, false), request: "x" });
    expect(rich).toContain("<li>가격 방향: 1~3만원 (확인 필요)</li>");
    expect(rich).toContain("<li>근거를 확인해 주세요.</li>");
  });
});
