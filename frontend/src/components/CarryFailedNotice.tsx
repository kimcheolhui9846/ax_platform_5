type Props = { busy: boolean; onContinue: () => void };

/** 이어 갈 이전 작업을 불러오지 못했을 때. 막다른 길 대신 가져오지 않고 계속할 수 있다. */
export function CarryFailedNotice({ busy, onContinue }: Props) {
  return (
    <div className="notice stack8" role="alert">
      <p>이전 작업을 불러오지 못했어요. 가져오지 않고 계속할 수 있어요.</p>
      <button type="button" className="btn compact" disabled={busy} onClick={onContinue}>
        가져오지 않고 계속
      </button>
    </div>
  );
}
