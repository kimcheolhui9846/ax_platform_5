// 테스트에서 쓰는 계산 시간 측정. 한 번의 튀는 값(GC 등)에 흔들리지 않게 중앙값을 쓴다.

/** 값들의 중앙값(짝수 개면 가운데 두 값의 평균). 받은 배열은 바꾸지 않는다. */
export function median(values: readonly number[]): number {
  if (values.length === 0) throw new Error("중앙값을 낼 값이 없다");
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/** run을 warmup번 돌려 데운 뒤 times번 재서, 한 번 걸린 시간(ms)의 중앙값을 낸다. */
export function medianMs(run: () => void, times = 500, warmup = 50): number {
  for (let i = 0; i < warmup; i += 1) run();
  const spent: number[] = [];
  for (let i = 0; i < times; i += 1) {
    const start = performance.now();
    run();
    spent.push(performance.now() - start);
  }
  return median(spent);
}
