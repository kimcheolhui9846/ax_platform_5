import type { KeyValueStore } from "./storage";

export const CLIENT_ID_KEY = "ax.client-id";
const CLIENT_ID = /^[A-Za-z0-9-]{8,64}$/; // 백엔드 app/api/owner.py와 같은 형식

export function isClientId(value: string): boolean {
  return CLIENT_ID.test(value);
}

/**
 * 이 브라우저의 익명 사용자 ID. 저장해 둔 값이 있으면 쓰고, 없거나 형식이 틀리면 새로 만들어 저장한다.
 * 저장소를 못 쓰면 이번 실행에서만 쓰는 ID가 된다(새로 고치면 다른 사용자로 보인다).
 */
export function loadClientId(storage: KeyValueStore | null, makeId: () => string): string {
  const saved = readSaved(storage);
  if (saved !== null && isClientId(saved)) return saved;
  const id = makeId();
  try {
    storage?.setItem(CLIENT_ID_KEY, id);
  } catch {
    // 저장하지 못해도 이번 실행에서는 쓴다
  }
  return id;
}

function readSaved(storage: KeyValueStore | null): string | null {
  try {
    return storage?.getItem(CLIENT_ID_KEY) ?? null;
  } catch {
    return null;
  }
}

type RandomSource = Pick<Crypto, "getRandomValues"> & Partial<Pick<Crypto, "randomUUID">>;

/** 새 ID. randomUUID는 보안 컨텍스트(https·localhost)에서만 있어 없으면 무작위 바이트로 만든다. */
export function makeClientId(source: RandomSource = crypto): string {
  if (source.randomUUID) return source.randomUUID();
  const bytes = source.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
