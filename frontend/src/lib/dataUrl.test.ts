import { describe, expect, it } from "vitest";

import { blobToDataUrl, bytesToDataUrl } from "./dataUrl";

describe("data URL", () => {
  it("바이트를 base64 data URL로 바꾼다", () => {
    expect(bytesToDataUrl("image/svg+xml", new TextEncoder().encode("<svg/>"))).toBe("data:image/svg+xml;base64,PHN2Zy8+");
  });

  it("큰 바이트도 한 번에 바꾼다(호출 스택을 넘기지 않는다)", () => {
    const bytes = new Uint8Array(300_000).fill(65);
    expect(bytesToDataUrl("image/png", bytes).length).toBe("data:image/png;base64,".length + 400_000);
  });

  it("Blob은 그 형식으로 바꾼다", async () => {
    expect(await blobToDataUrl(new Blob(["<svg/>"], { type: "image/svg+xml" }))).toBe("data:image/svg+xml;base64,PHN2Zy8+");
  });
});
