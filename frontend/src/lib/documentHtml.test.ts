import { describe, expect, it } from "vitest";

import { makeResult, makeTask } from "../testing/factories";
import { documentContent } from "./document";
import { documentHtml, escapeHtml } from "./documentHtml";

describe("내려받을 문서(HTML)", () => {
  it("글자를 이스케이프한다", () => {
    expect(escapeHtml(`<script>alert("x")</script> & '`)).toBe("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &#39;");
  });

  it("제목·위 줄·요청·기준·섹션을 담은 한 파일이다", () => {
    const content = documentContent(makeTask(), makeResult(), false, {});
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
    const base = { ...documentContent(makeTask(), makeResult(), false, {}), request: "향초" };
    expect(documentHtml(base)).not.toContain("보완 정보");
    const html = documentHtml({ ...base, supplements: [{ label: "소재", value: "<면>" }] });
    expect(html).toContain("<h2>보완 정보 · 사용자 입력 / 검증 전</h2>");
    expect(html).toContain("<tr><th>소재</th><td>&lt;면&gt;</td></tr>");
  });

  it("AI 가정과 검토 항목은 있을 때만 넣는다", () => {
    const plain = documentHtml({ ...documentContent(makeTask(), makeResult(), false, {}), request: "x" });
    expect(plain).not.toContain("AI가 가정한 내용");
    expect(plain).not.toContain("검토가 필요한 부분");

    const shown = makeResult({ validation: { issues: [{ rule: "r", message: "근거를 확인해 주세요.", severity: "warning" }], passed: true } });
    shown.result.assumptions = [{ field: "price", label: "가격 방향", value: "1~3만원", reason: "", requires_confirmation: true }];
    const rich = documentHtml({ ...documentContent(makeTask(), shown, false, {}), request: "x" });
    expect(rich).toContain("<li>가격 방향: 1~3만원 (확인 필요)</li>");
    expect(rich).toContain("<li>근거를 확인해 주세요.</li>");
  });

  it("이미지는 data URL일 때만 넣고, 근거 기록은 출처 링크와 함께 싣는다", () => {
    const result = makeResult();
    const content = documentContent(
      makeTask(),
      {
        ...result,
        result: {
          ...result.result,
          sections: [
            {
              order: 1,
              heading: "콘셉트",
              kind: "diagnosis",
              blocks: [
                { type: "text", text: "글" },
                { type: "image", asset_id: "a", alt: "참고 <이미지>", caption: "AI 참고", origin: "ai_generated" },
                { type: "image", asset_id: "b", alt: "못 불러옴", caption: "", origin: "ai_generated" },
              ],
            },
          ],
          evidence: [
            { source_id: "z", title: "점검", text: "점검 문구", note: "제품 시험 전", source_title: "자료", publisher: "기관", url: "https://x.kr/a?b=1&c=2", section_kind: "diagnosis", section_order: 1 },
          ],
        },
      },
      false,
      { a: "data:image/svg+xml;base64,AA", b: null },
    );

    const html = documentHtml({ ...content, request: "요청" });

    expect(html).toContain('<figure><img src="data:image/svg+xml;base64,AA" alt="참고 &lt;이미지&gt;"><figcaption>AI 참고</figcaption></figure>');
    expect(html).toContain('<p class="note">[이미지: 못 불러옴]</p>');
    expect(html).toContain("근거 검토 반영 · 점검");
    expect(html).toContain('<a href="https://x.kr/a?b=1&amp;c=2">출처: 기관 · 자료</a>');
  });
});
