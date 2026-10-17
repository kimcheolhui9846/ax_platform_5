import { describe, expect, it } from "vitest";

import { CLIENT_ID_KEY, isClientId, loadClientId, makeClientId } from "./clientId";
import type { KeyValueStore } from "./storage";

function memoryStore(initial: Record<string, string> = {}): KeyValueStore & { data: Map<string, string> } {
  const data = new Map(Object.entries(initial));
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

describe("isClientId", () => {
  it("백엔드와 같은 형식(영문·숫자·하이픈 8~64자)만 받는다", () => {
    expect(isClientId("3f2b8c1e-9a4d-4c2b-8f1e-2a3b4c5d6e7f")).toBe(true);
    expect(isClientId("short")).toBe(false);
    expect(isClientId("bad id!!")).toBe(false);
    expect(isClientId("a".repeat(65))).toBe(false);
  });
});

describe("loadClientId", () => {
  it("저장해 둔 ID가 있으면 그대로 쓴다", () => {
    const store = memoryStore({ [CLIENT_ID_KEY]: "saved-client-01" });
    expect(loadClientId(store, () => "new-client-0001")).toBe("saved-client-01");
  });

  it("없거나 형식이 틀리면 새로 만들어 저장한다", () => {
    const empty = memoryStore();
    expect(loadClientId(empty, () => "new-client-0001")).toBe("new-client-0001");
    expect(empty.data.get(CLIENT_ID_KEY)).toBe("new-client-0001");

    const broken = memoryStore({ [CLIENT_ID_KEY]: "bad id!!" });
    expect(loadClientId(broken, () => "new-client-0002")).toBe("new-client-0002");
  });

  it("저장소를 못 쓰면 이번 실행에서만 쓰는 ID를 만든다", () => {
    expect(loadClientId(null, () => "new-client-0003")).toBe("new-client-0003");
    expect(loadClientId(blocked, () => "new-client-0004")).toBe("new-client-0004");
  });
});

describe("makeClientId", () => {
  const getRandomValues = crypto.getRandomValues.bind(crypto);

  it("randomUUID가 있으면 쓴다", () => {
    const uuid = "3f2b8c1e-9a4d-4c2b-8f1e-2a3b4c5d6e7f" as const;
    expect(makeClientId({ randomUUID: () => uuid, getRandomValues })).toBe(uuid);
  });

  it("없으면(보안 컨텍스트 밖) 무작위 32자 16진수를 만든다", () => {
    const id = makeClientId({ getRandomValues });
    expect(id).toMatch(/^[0-9a-f]{32}$/);
    expect(isClientId(id)).toBe(true);
  });
});
