import { describe, expect, it } from "vitest";

import { readDraft, writeDraft } from "./drafts";
import type { KeyValueStore } from "./storage";

function memoryStore(): KeyValueStore & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  };
}

const blocked: KeyValueStore = {
  getItem: () => {
    throw new Error("blocked");
  },
  setItem: () => {
    throw new Error("blocked");
  },
  removeItem: () => {
    throw new Error("blocked");
  },
};

describe("요청 초안", () => {
  it("과제별로 저장하고 읽는다", () => {
    const store = memoryStore();
    writeDraft(store, "branding", "한글 파우치 브랜드");
    expect(readDraft(store, "branding")).toBe("한글 파우치 브랜드");
    expect(readDraft(store, "product_planning")).toBe("");
  });

  it("빈 글을 쓰면 지운다", () => {
    const store = memoryStore();
    writeDraft(store, "branding", "초안");
    writeDraft(store, "branding", "");
    expect(store.data.size).toBe(0);
  });

  it("저장소가 없거나 막혀도 실패하지 않는다", () => {
    expect(readDraft(null, "branding")).toBe("");
    expect(readDraft(blocked, "branding")).toBe("");
    expect(() => writeDraft(blocked, "branding", "x")).not.toThrow();
    expect(() => writeDraft(null, "branding", "x")).not.toThrow();
  });
});
