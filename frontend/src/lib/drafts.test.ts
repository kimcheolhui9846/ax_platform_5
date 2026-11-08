import { describe, expect, it } from "vitest";

import {
  answerDraftKey,
  inputDraftWrites,
  isInputDraftKey,
  readDraft,
  readInputDraft,
  reviseDraftKey,
  sectionDraftKey,
  writeDraft,
  writeInputDraft,
} from "./drafts";
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

describe("입력 초안", () => {
  it("키는 세션과 질문(또는 섹션 번호)으로 만들고 요청 글 키와 겹치지 않는다", () => {
    expect(answerDraftKey("s1", "q1")).toBe("answer:s1:q1");
    expect(reviseDraftKey("s1", "q1")).toBe("revise:s1:q1");
    expect(sectionDraftKey("s1", 2)).toBe("section:s1:2");
    expect(answerDraftKey("s1", "q1")).not.toBe(reviseDraftKey("s1", "q1"));
    expect(isInputDraftKey(answerDraftKey("s1", "q1"))).toBe(true);
    expect(isInputDraftKey("branding")).toBe(false);
  });

  it("키별로 저장하고 읽고 지운다(요청 글과 섞이지 않는다)", () => {
    const store = memoryStore();
    writeInputDraft(store, "answer:s1:q1", "내 답");
    writeDraft(store, "branding", "요청");
    expect(readInputDraft(store, "answer:s1:q1")).toBe("내 답");
    expect(readInputDraft(store, "answer:s1:q2")).toBe("");
    expect(readDraft(store, "answer:s1:q1")).toBe("");
    writeInputDraft(store, "answer:s1:q1", null);
    expect(readInputDraft(store, "answer:s1:q1")).toBe("");
    expect(store.data.size).toBe(1);
    writeInputDraft(store, "answer:s1:q1", "x");
    writeInputDraft(store, "answer:s1:q1", "");
    expect(store.data.size).toBe(1);
  });

  it("저장소가 없거나 막혀도 실패하지 않는다", () => {
    expect(readInputDraft(null, "answer:s1:q1")).toBe("");
    expect(readInputDraft(blocked, "answer:s1:q1")).toBe("");
    expect(() => writeInputDraft(blocked, "answer:s1:q1", "x")).not.toThrow();
    expect(() => writeInputDraft(null, "answer:s1:q1", null)).not.toThrow();
  });

  it("상태가 바뀐 입력 초안만 저장소 할 일로 만든다(없어진 키는 지우기)", () => {
    const prev = { branding: "요청", "answer:s1:q1": "a", "revise:s1:q2": "b" };
    const next = { branding: "요청 수정", "answer:s1:q1": "a2", "section:s1:1": "c" };
    expect(inputDraftWrites(prev, next)).toEqual([
      { key: "answer:s1:q1", text: "a2" },
      { key: "section:s1:1", text: "c" },
      { key: "revise:s1:q2", text: null },
    ]);
    expect(inputDraftWrites(next, next)).toEqual([]);
  });
});
