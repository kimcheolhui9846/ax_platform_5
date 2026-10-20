# 결과 문서 내보내기(PDF·Word)와 예시 문구 교체 설계

- 날짜: 2026-10-20
- 브랜치: `task/31-document-export`

## 목적

결과 문서를 지금의 HTML 한 가지가 아니라 PDF·Word(.docx)로도 내보낸다. 요청 화면 예시를 '향초'에서 '한글 북백'(한글 디자인 가방)으로 바꾼다. 디자인은 나중에 다시 받으므로 기능 위주로 만든다.

## 결정 사항

- 형식은 PDF·Word(.docx)·HTML 세 가지. HWP는 만들지 않는다(바이너리 `.hwp`는 쓸 만한 JS 라이브러리가 없고, HWPX는 검증 부담이 크다). 한글(한컴)에서는 .docx를 열 수 있다.
- PDF는 브라우저 인쇄(`print()`)의 'PDF로 저장'으로 만든다. 한글 글꼴 내장 문제와 라이브러리가 없다. 파일 이름은 문서 `<title>`을 따른다.
- Word는 `docx` 라이브러리로 브라우저에서 만든다. 서버는 바뀌지 않는다(API 계약 변경 없음). 내려받기를 누를 때 dynamic import로 불러 첫 화면 번들에 넣지 않는다.
- 버튼은 하나('문서 내려받기')이고 누르면 형식 메뉴가 열린다(PDF · Word(.docx) · HTML).
- HTML 내려받기는 남긴다(이미지까지 한 파일로 보관).

## 구조

### 내용 (변경 없음)

세 형식 모두 `lib/document.ts`의 `documentContent`(+ 요청 글)를 쓴다. 형식마다 내용이 갈라지지 않는다.

### 형식별 생성

- `lib/documentHtml.ts` — 그대로. 인쇄용 CSS(`@page` 여백, 섹션 제목 뒤·그림·근거 기록 안에서 페이지가 끊기지 않게)를 `STYLE`에 `@media print`로 더한다. HTML 파일을 인쇄해도 같은 결과다.
- `lib/documentDocx.ts`(새) — `documentDocx(content & {request}): Document`(순수, `docx`의 `Document` 객체). 구성은 HTML과 같은 순서: 작은 줄(kicker) · 제목 · 내 요청 · 기준 표(비공개 표시 포함) · 섹션(번호·제목·종류, 본문 문단, 이미지, 근거 기록) · 자리 없는 근거 기록 · 보완 정보 표 · 가정 목록 · 검토 목록 · 맺음 문구. 본문의 줄바꿈은 줄 나눔으로 옮긴다. 이미지는 data URL이 `image/png`·`image/jpeg`일 때만 넣고(크기는 폭 상한에 맞춰 비율 유지, 원본 크기를 모르면 고정 폭), 그 밖(SVG·실패·불러오는 중)은 `[이미지: 대체 글]` 문단이다.
- `lib/download.ts` — 부수 효과만 둔다.
  - `saveBlob(filename, blob)` — 지금의 링크 클릭 저장.
  - `printHtml(html)` — 보이지 않는 iframe에 `srcdoc`로 넣고 load 뒤 `contentWindow.print()`, 끝나면(`afterprint` 또는 시간 초과) iframe을 지운다. 새 창을 열지 않아 팝업 차단에 걸리지 않는다.
  - `exportDocument(file, format): Promise<void>` — 형식별로 위를 부른다. docx는 `import("docx")` 후 `Packer.toBlob`.

### 내보낼 문서

`app/documentFile.ts`의 `documentFileOf(model)`은 `DocumentFile = { basename, content }`를 돌려준다. `basename`은 `AX_{task}_V{n}`, `content`는 `DocumentContent & { request }`(형식 무관)다. HTML·docx로 바꾸고 확장자를 붙이는 일은 `exportDocument`가 형식에 따라 한다. `DocumentFile` 타입은 `lib/documentHtml.ts`에서 `lib/document.ts`로 옮긴다.

### 화면·처리

- `DocumentFormat = "pdf" | "docx" | "html"`과 메뉴 항목 문구(`DOCUMENT_FORMATS`: 값·라벨)는 `lib/documentFormats.ts`(순수).
- `Handlers.download(file, format)`. `handlers.ts`는 App이 넘긴 `exportDocument`를 부르고, 끝나면 알림을 낸다.
  - html·docx: `문서를 내려받았어요.`
  - pdf: `인쇄 창에서 'PDF로 저장'을 고르세요.`
  - 실패(라이브러리 불러오기·생성 실패): `문서를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.`
  - PDF 실패(인쇄용 문서가 10초 안에 열리지 않거나 인쇄를 시작하지 못함): `인쇄 창을 열지 못했어요. 브라우저의 인쇄·팝업 차단을 확인하거나 Word·HTML로 받아 주세요.`
  - 만드는 중(`state.exporting`, 리듀서의 `exportStarted`·`exportFinished`)에 다시 누르면 만들지 않고: `문서를 만드는 중이에요. 끝난 뒤 다시 눌러 주세요.`
- `components/DownloadMenu.tsx`(새) — 버튼 + 펼침 목록(disclosure: `aria-expanded`, `aria-controls`). 항목을 고르면 `onDownload(format)` 후 닫고, Esc로 닫으면 버튼으로 포커스를 돌린다. 열림 상태만 부품이 가진다. `disabled`·`aria-describedby`(최신 아님 안내)를 받는다.
- 결과(`ResultScreen`의 오른쪽)·저장 완료(`SavedScreen`)·버전 보기(`VersionScreen` 오른쪽)의 '문서 내려받기' 버튼을 `DownloadMenu`로 바꾼다. 낡은 결과일 때 막는 규칙은 그대로.
- 미리보기: 메뉴가 열린 결과 화면 프레임을 하나 더한다(`DownloadMenu`의 `initialOpen`).

## 예시 문구

`policy.yaml`의 `input_placeholder`·`input_examples` 첫 항목(두 번째 예시는 그대로):

| 과제 | 새 예시 |
|---|---|
| 사업계획 | 한글 디자인 북백을 온라인으로 팔고 싶어요 |
| 상품기획 | 외국인 관광객 선물용 한글 북백 |
| 브랜딩 | 책 좋아하는 20대를 위한 한글 북백 |
| 마케팅 콘텐츠 | 한글날 한정 한글 북백을 알리고 싶어요 |

상품기획 분류 선택지 `향초·디퓨저` → `가방·패션잡화`. `preview/fixtures.ts`의 예시, `docs/DEMO.md` 시연 입력, `docs/HANDOFF.md`의 스모크 예시도 바꾼다. 테스트·평가 시나리오의 향초 데이터는 화면에 나오지 않으므로 그대로 둔다(정책 선택지를 참조하는 테스트가 있으면 같이 고친다).

## 테스트

- `documentDocx`: `Packer`로 만든 파일을 풀어 `word/document.xml`에 제목·섹션 제목·기준 값·특수문자(`<`, `&`)가 바르게 들어갔는지, PNG 이미지는 미디어로, SVG는 대체 글로 들어갔는지.
- `documentHtml`: `@media print` 규칙이 있다.
- `documentFileOf`: 결과·저장·버전 화면에서 `basename`·내용, 그 밖은 null.
- `DownloadMenu`: 열기, 항목 선택 시 형식 전달·닫힘, Esc 닫힘·포커스 복귀, 막힘.
- `handlers`: 형식별 알림, 실패 알림.
- 백엔드: `uv run --directory backend pytest`(정책 변경 확인).

## 범위 밖

HWP/HWPX, 서버 쪽 PDF 생성, 내보내기 디자인 다듬기(디자이너 수정본이 오면 반영).
