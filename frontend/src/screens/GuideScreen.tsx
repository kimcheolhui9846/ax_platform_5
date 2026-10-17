const STEPS: [string, string][] = [
  ["01 요청과 코칭", "하고 싶은 일을 보낸 뒤 빠른·스탠다드·정밀 중 하나를 고르세요."],
  [
    "02 질문과 흐름",
    "한 번에 하나씩 답하고, 오른쪽에서 완료·현재·예정을 확인하세요. 어려우면 '다른 예시 보기', 아직 정하지 못했으면 '아직 모르겠어요'를 누르세요.",
  ],
  ["03 답변 확인과 초안", "이해한 기준을 확인하고 초안을 만드세요. 언제든 현재 정보로 초안을 만들 수 있어요."],
  ["04 결과와 수정", "결과를 보고 기준 답변을 바꾸거나 남은 질문을 이어 가면 초안을 다시 만들 수 있어요."],
];

/** 흐름 안내. */
export function GuideScreen({ onStart }: { onStart: () => void }) {
  return (
    <section className="guide stack">
      <p className="small">CREATOR AX · 흐름 안내</p>
      <h1 className="screen-title">질문은 하나씩, 맥락은 끝까지</h1>
      <p className="bodycopy">요청 → 코칭 모드 → 질문·확인 → 결과</p>
      <div className="taskgrid">
        {STEPS.map(([heading, body]) => (
          <div key={heading} className="card stack12">
            <h2>{heading}</h2>
            <p className="muted">{body}</p>
          </div>
        ))}
      </div>
      <button type="button" className="btn primary" onClick={onStart}>
        과제 선택하고 시작하기
      </button>
    </section>
  );
}
