# AI 동시 호출 상한 설계

- 작성일: 2026-10-19
- 배경: 라우터는 동기 함수라 스레드 풀(기본 40개)에서 돈다. 실제 모델 호출은 수십 초가 걸리므로 생성 요청이 몰리면 스레드와 메모리를 오래 잡아, 세션 조회 같은 가벼운 요청까지 막힌다. 렌더 Free(512MB)처럼 서버를 늘릴 수 없는 환경에서 부하 상한을 "사용자 수"가 아니라 "설정값"에 묶는다.
- 범위: 비용 0. Mock과 테스트용 제공자로 확인한다. 워커(프로세스) 하나를 전제로 한다(세션 잠금·SQLite와 같은 전제).

## 1. 결정 사항 (사용자 확정)

| # | 주제 | 결정 |
|---|---|---|
| 1 | 구조 | 제공자를 감싸는 `LimitedProvider`·`LimitedImageProvider`. 둘이 자리(`CallSlots`) 하나를 같이 쓴다. 하네스의 `_call`·`illustrate`는 그대로 |
| 2 | 자리가 없을 때 | 정해진 시간만 기다렸다가 못 얻으면 거절(503 + `Retry-After`) |

## 2. 원칙

- **붐빔은 생성 실패가 아니다.** 자리를 못 얻으면 세션을 바꾸지 않는다. 질문 단계는 이미 원자적이고, `generate`는 `ProviderBusy`를 `HarnessError`처럼 그대로 올려 되돌린다(`FAILED`로 바꾸지 않는다).
- **보조 단계는 지금처럼 줄인다.** LLM 검토·이미지가 붐빔에 걸리면 경고(`llm_review_unavailable`·`image_unavailable`)로 줄이고 결과는 살린다(`ProviderBusy`는 `ProviderError`의 하위 클래스).
- **Mock도 감싼다.** 비용은 0이고 운영과 같은 길로 돈다.

## 3. 백엔드

- `app/providers/base.py`: `ProviderBusy(ProviderError)`.
- `app/providers/limit.py`:
  - `CallSlots(size, wait_seconds)`: `threading.BoundedSemaphore`. `hold()`는 최대 `wait_seconds` 기다려 자리를 얻고, 못 얻으면 `ProviderBusy`. 예외가 나도 자리를 돌려준다.
  - `LimitedProvider(inner, slots)`: `complete`를 자리 안에서 넘긴다. `name`은 `inner.name`.
  - `LimitedImageProvider(inner, slots)`: `generate`를 같은 방식으로.
- `app/config.py`: `ai_max_concurrent_calls: PositiveInt = 4`, `ai_queue_wait_seconds: NonNegativeFloat = 10`(환경 변수 `AI_MAX_CONCURRENT_CALLS`·`AI_QUEUE_WAIT_SECONDS`).
- `app/main.py`: 자리 하나를 만들어 LLM·이미지 제공자를 감싼다. 테스트가 넘긴 제공자도 감싼다(`create_app`에 `slots` 인자, 없으면 설정값).
- `app/core/messages.py`: `AI_BUSY_MESSAGE = "지금 요청이 많아요. 잠시 후 다시 시도해 주세요."`.
- `app/api/errors.py`: `ProviderBusy` → 503, `Retry-After: 5`. Starlette는 예외 클래스의 MRO 순서로 처리기를 찾으므로 `ProviderError`(502)보다 먼저 잡힌다.
- `app/api/responses.py`·`coaching.py`: 502를 낼 수 있는 경로마다 503을 함께 적는다.

## 4. 프론트

503도 JSON `{detail}`이라 지금 처리 그대로 알림으로 나간다. 생성 요청은 지금 422와 같이 실패 화면 + 알림. `gen:api` 뒤 빌드·테스트만 확인한다.

## 5. 테스트

- `CallSlots`: 자리가 다 차면 대기 시간 뒤 `ProviderBusy`, 돌려주면 다음이 들어간다, 예외가 나도 돌려준다.
- `LimitedProvider`·`LimitedImageProvider`: 자리 안에서 넘기고, 자리가 없으면 안쪽을 부르지 않는다.
- 하네스: `generate`에서 `ProviderBusy`가 나면 상태·결과·버전이 그대로(FAILED 아님)이고 예외가 올라온다.
- API: 자리 하나·대기 0초인 앱에서 테스트가 자리를 먼저 잡아 둔 채 세션 만들기·생성이 503 + `Retry-After`, 세션은 그대로.
- 설정: 0 이하 상한은 거부.

## 6. 범위 밖

- 여러 프로세스 간 상한(공유 저장소 잠금이 필요해질 때 함께).
- 과제 안 변형 파이프라인 선택(n중 파이프라인). 메모리는 파이프라인 수가 아니라 동시 요청 수에 비례하므로 이 상한과 독립이다. 측정(`docs/HARNESS-ROADMAP.md` 0단계) 뒤 별도 작업.
