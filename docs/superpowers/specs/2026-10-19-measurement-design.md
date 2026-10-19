# 측정 준비 설계 (비용 0)

- 작성일: 2026-10-19
- 배경: 로드맵 0단계(`docs/HARNESS-ROADMAP.md`)와 병렬 생성 측정표를 채우려면 실제 모델 비용이 든다. 비용이 들기 전에 할 수 있는 준비를 모두 끝내, 유료 실행은 명령 한 줄로 짧게 끝나게 한다.

## 1. 응답 시간 기록
- `TraceEntry.duration_ms: int | None`. 제공자를 부른 기록(성공·실패·유출 차단, 이미지 포함)은 걸린 시간, 부르지 않은 기록(검증 요약, 병렬 생성의 캐시 사용)은 None.
- 재는 곳: `BaseHarness._send`(LLM), `illustrate`(이미지). `time.perf_counter`.
- trace 응답에 실리므로 API 타입이 바뀐다(`gen:api`).

## 2. 시나리오 실행 둘로 나누기 (`app/harness/evals.py`)
- `play_questions(harness, scenario) -> PlayedScenario(state, mismatches)`: 질문 단계만. 범위 밖 선택지는 '아직 모르겠어요'로 대신하고, 쓰이지 않은 답과 함께 `mismatches`로 돌려준다. 모르는 필드에 계획한 답은 시나리오 오류라 바로 실패한다.
- `run_scenario`(Mock 회귀): `play_questions` 뒤 어긋남이 있으면 시나리오 이름과 함께 실패, 없으면 생성. 지금 계약 그대로.
- 과제마다 `evals/quick-skip.yaml`: 빠른 모드, 모든 질문 '아직 모르겠어요'. 실제 모델에서도 계획이 어긋나지 않고 정보가 적을 때 가정·미정 처리를 본다.

## 3. 측정 도구
- 로직 `app/harness/measure.py`, 실행 `scripts/measure.py`(기본 Mock).
- 과제 × 시나리오 × 방식(`single` 한 번 호출, `parallel` 병렬) × 반복. 병렬 조각은 `scripts/measure_parallel.yaml`이고 측정용 임시 폴더의 정책에만 붙인다(실제 과제 정책은 꺼진 그대로).
- 실행 한 줄(`RunRow`): 상태, 질문·생성 벽시계 시간, 호출 수, 실패 호출(형식·잘림·거절·유출), 유출 차단, 토큰(입력·출력·캐시 읽기·쓰기), 검증 경고, 계획 어긋남, 모델 id, 추정 비용. 예외는 `error`에 남기고 다음 실행으로 넘어간다.
- 비용: 단가표(HANDOFF 참고 단가, 캐시 읽기 0.1배·쓰기 1.25배)로 추정. Mock은 0, 모르는 모델이 섞이면 비용 칸이 비어(-) 상한에 더하지 않는다.
- 안전장치: `--provider claude`는 `--budget-usd` 없이는 돌지 않는다. 누적 추정 비용이 상한에 닿으면 다음 실행부터 멈춘다(추정이므로 콘솔 사용 한도도 함께 건다).
- 결과: `backend/data/measure/<시각>/rows.csv`, `summary.md`(과제·방식별 생성 p50·p95 등 요약 표). `backend/data/`는 git에서 빠진다.
