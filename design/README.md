# 디자인 HTML 원본

디자인 팀원이 피그마에서 내보낸 프로토타입 HTML을 **받은 그대로** 보관한다. 이 폴더의 파일은 고치지 않는다.

## 새 디자인을 받았을 때

1. `design/YYYY-MM-DD[-설명]/` 폴더를 만들고 HTML과 에셋을 그대로 넣는다.
2. 직전 버전과 비교한다: `git diff --no-index design/<이전 폴더> design/<새 폴더>`
3. 화면·상태(설계서 9.3: 초기·정보 부족·생성 중·완료·실패·수정)를 대조해 API가 바뀌어야 하는지 먼저 정리한다.
4. API가 바뀌면 백엔드 `app/schemas/`를 고치고 `npm --prefix frontend run gen:api`로 프론트 타입을 다시 만든다.
5. React 컴포넌트에 바뀐 화면만 반영한다.

## 개발 화면을 피그마로 가져가기 (html.to.design)

1. 미리보기 주소를 연다. 버셀 정식 주소의 `/preview`를 쓰고, PR이면 그 PR의 미리보기 주소에 `/preview`를 붙인다.
   - 로컬에서는 `npm --prefix frontend run dev`를 켜고 `http://localhost:5173/preview`을 연다.
2. 피그마에서 html.to.design 플러그인으로 그 주소를 가져온다.
   - 로컬 주소는 플러그인의 Chrome 확장으로 현재 페이지를 가져온다.
   - 프레임마다 `data-screen` 이름표(예: `question-desktop`)가 붙어 있다.
3. 피그마에서 수정한다. 색·글꼴·간격처럼 여러 화면에 걸친 값을 바꿨다면 바꾼 값을 따로 적어 개발에 넘긴다.
   - 그 값은 `frontend/src/styles/tokens.css` 한 곳에서 고친다.
4. 수정본을 HTML로 내보내 새 `design/YYYY-MM-DD[-설명]/` 폴더에 넣는다.
5. 개발은 위 "새 디자인을 받았을 때" 절차로 바뀐 화면을 반영한다.
