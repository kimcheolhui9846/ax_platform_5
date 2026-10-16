import { FRAMES, FRAME_SIZES } from "./frames";

/** 모든 화면 상태를 PC·모바일 폭으로 나란히 그린다. html.to.design으로 프레임 단위 가져오기를 한다. */
export function Gallery() {
  return (
    <div className="gallery">
      <header className="gallery-intro stack8">
        <h1>창작자 AX · 화면 미리보기</h1>
        <p className="muted">
          백엔드 없이 샘플 데이터로 그린 모든 화면 상태입니다. 피그마에서 html.to.design 플러그인으로 이 페이지 주소를
          가져오면 프레임별로 편집할 수 있어요.
        </p>
      </header>
      {FRAMES.map((frame) => (
        <section key={frame.id} className="gallery-row stack12">
          <h2 className="gallery-title">{frame.title}</h2>
          <div className="gallery-frames">
            {FRAME_SIZES.map((size) => (
              <div key={size} className={`gallery-frame gallery-frame-${size}`} data-screen={`${frame.id}-${size}`}>
                {frame.render(`${frame.id}-${size}-main`)}
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
