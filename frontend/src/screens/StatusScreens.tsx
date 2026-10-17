export function LoadingScreen() {
  return (
    <p className="card muted" role="status">
      불러오는 중이에요…
    </p>
  );
}

type Props = { onRetry: () => void; onHome: () => void };

/** 화면에 필요한 데이터를 받지 못했다(없는 세션·과제, 백엔드 꺼짐). */
export function UnavailableScreen({ onRetry, onHome }: Props) {
  return (
    <section className="card confirm stack" role="alert">
      <h1>화면을 불러오지 못했어요</h1>
      <p className="muted">주소가 맞는지, 백엔드가 켜져 있는지 확인한 뒤 다시 시도해 주세요.</p>
      <div className="row">
        <button type="button" className="btn primary" onClick={onRetry}>
          다시 시도
        </button>
        <button type="button" className="btn" onClick={onHome}>
          과제 선택으로
        </button>
      </div>
    </section>
  );
}
