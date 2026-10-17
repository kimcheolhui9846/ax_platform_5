type Props = { title: string; body: string; onHome: () => void };

/** 목록이 비었을 때. 과제 선택으로 이끈다. */
export function EmptyState({ title, body, onHome }: Props) {
  return (
    <div className="card empty stack">
      <h2>{title}</h2>
      <p className="muted">{body}</p>
      <button type="button" className="btn" onClick={onHome}>
        과제 선택하기
      </button>
    </div>
  );
}
