const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** [순수] ISO 시각을 한국 시각 "YYYY.MM.DD HH:mm"으로. 실행 환경의 시간대와 상관없이 같은 값이 나온다. */
export function formatDate(iso: string): string {
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return iso;
  const d = new Date(time + KST_OFFSET_MS);
  return `${d.getUTCFullYear()}.${pad(d.getUTCMonth() + 1)}.${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}
