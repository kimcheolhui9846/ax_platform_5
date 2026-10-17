/** 알림 한 줄. 화면 읽기 프로그램이 읽도록 자리는 늘 두고 내용만 바꾼다. */
export function Toast({ message }: { message: string | null }) {
  return (
    <div className="toast" role="status" aria-live="polite" hidden={message === null}>
      {message ?? ""}
    </div>
  );
}
