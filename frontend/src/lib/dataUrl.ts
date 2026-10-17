const CHUNK = 0x8000;

/** [순수] 바이트를 base64 data URL로. 조각으로 나눠 String.fromCharCode의 인자 수 한계를 넘지 않는다. */
export function bytesToDataUrl(mime: string, bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
  }
  return `data:${mime};base64,${btoa(binary)}`;
}

/** 받은 이미지(Blob)를 data URL로. 화면 <img>와 내려받는 문서가 같은 값을 쓴다. */
export async function blobToDataUrl(blob: Blob): Promise<string> {
  return bytesToDataUrl(blob.type, new Uint8Array(await blob.arrayBuffer()));
}
