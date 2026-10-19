# 단계별 모델 라우팅 설계 (로드맵 1단계)

- 작성일: 2026-10-19
- 배경: `docs/HARNESS-ROADMAP.md` 3장. 지금은 모든 단계(진단·쉬운 질문·후보 제안·생성·검토)가 모델 하나(`CLAUDE_MODEL`)와 노력 하나(`CLAUDE_EFFORT`)를 쓴다. 단계마다 모델·노력을 설정으로 고를 수 있게 해, 인수 팀이 0단계 측정 뒤 약한 단계만 올리거나 가벼운 단계를 싸게 돌릴 수 있게 한다.
- 범위: 비용 0. 실제 호출 없이 Mock 테스트와 가짜 전송(SDK 클라이언트 + MockTransport)으로 확인한다.

## 1. 결정 사항 (사용자 확정)

| # | 주제 | 결정 |
|---|---|---|
| 1 | 구조 | 제공자를 감싸는 `RoutedProvider`(단계 → 제공자). 하네스·`_call`은 그대로 |
| 2 | 기본값 | 꺼 둠. 설정이 없으면 지금과 똑같다. `.env.example`에 예시를 주석으로 둔다 |

## 2. 원칙

- **하네스는 모른다.** `LLMProvider.complete(task_type, stage, prompt, response_model)`가 이미 단계를 받으므로, 라우팅은 제공자 쪽에서 끝난다. 하네스·프롬프트·trace 형식은 바뀌지 않는다(trace에는 이미 실제 모델 id `model`이 남는다).
- **고르기는 순수 함수다.** 단계 → 제공자 판단은 값만 받아 값을 돌려준다.
- **오타는 시작 때 실패한다.** 없는 단계 이름, 허용되지 않는 노력 값은 설정을 읽을 때 거부한다(정책 YAML이 모르는 키를 거부하는 것과 같은 원칙).
- **Mock은 라우팅하지 않는다.** `PROVIDER=mock`이면 단계 설정이 있어도 MockProvider 하나다(비용 0, 테스트 그대로).

## 3. 백엔드

### 3.1 설정 (`app/config.py`)
- `claude_stage_models: dict[str, str] = {}` — 단계 → 모델 id. 환경 변수 `CLAUDE_STAGE_MODELS`(JSON).
- `claude_stage_efforts: dict[str, Effort] = {}` — 단계 → 노력. 환경 변수 `CLAUDE_STAGE_EFFORTS`(JSON). `Effort = Literal["low", "medium", "high", "xhigh", "max"]`(지금 `claude_effort`와 같은 타입을 한 곳에 둔다).
- 두 사전의 키는 LLM 단계(`prompting.STAGES` 중 `image` 제외 — 이미지는 `ImageProvider`라 이 라우팅 밖이다)여야 한다. 아니면 설정 검증 실패(서버 시작 실패). 메시지에 허용 단계 이름을 싣는다.
- 단계 하나에 모델만 또는 노력만 정할 수 있다. 정하지 않은 쪽은 기본(`claude_model`·`claude_effort`)을 쓴다.

### 3.2 고르기 (`app/providers/routing.py`, 순수)
- `stage_targets(default_model, default_effort, stage_models, stage_efforts) -> dict[str, tuple[str, str]]`: 설정에 나온 단계마다 (모델, 노력)을 채운다. 결과가 기본과 같은 단계는 넣지 않는다(쓸데없는 제공자를 만들지 않는다).
- `RoutedProvider(default: LLMProvider, routes: Mapping[str, LLMProvider])`: `complete`는 `routes.get(stage, default)`에 그대로 넘긴다. `name`은 `default.name`(지금은 모두 Claude라 같다. 다른 종류를 섞게 되면 trace의 `provider` 기록을 다시 정한다 — 로드맵 2단계).

### 3.3 조립 (`app/providers/factory.py`)
- `get_provider(name, *, model, effort, stage_models, stage_efforts)`: `mock`이면 지금처럼 MockProvider. `claude`면 기본 `ClaudeProvider(model, effort)`를 만들고, `stage_targets`가 비어 있으면 그것을 그대로 돌려준다(설정이 없으면 지금과 같은 객체). 아니면 (모델, 노력)마다 `ClaudeProvider`를 하나씩 만들어(같은 조합은 하나를 같이 쓴다) `RoutedProvider`로 감싼다.
- `app/main.py`는 설정 두 개를 더 넘긴다.
- 클라이언트: 각 `ClaudeProvider`는 지금처럼 자기 SDK 클라이언트를 만든다(키 확인도 그대로).

### 3.4 모델별 차이
- 대체 모델(`fallbacks`)은 이미 모델별로 정한다(Haiku는 보내지 않는다, `_supports_fallbacks`). 라우팅으로 Haiku를 쓴 단계도 그 규칙을 따른다.
- 노력은 Haiku 5.5·Sonnet 5.5·Opus 5.5 모두 `low`~`max`를 받는다. 기본값은 모델마다 다르므로(Opus 5.5·Haiku 5.5는 medium, Sonnet 5.5는 high) 우리처럼 늘 노력을 명시해 보내는 것이 맞다.
- 캐시는 모델마다 따로다. 단계마다 system이 이미 달라 캐시도 단계별이므로, 라우팅이 캐시를 잃게 하지는 않는다.

## 4. 문서

- `backend/.env.example`: 주석 예시 두 줄과 설명(가벼운 단계를 Haiku로, 생성 노력 올리기. 측정 전에는 켜지 말 것, 로드맵 링크).
- `docs/HARNESS-ROADMAP.md` 3장: "구현됨(task/26)"과 설정 이름.
- `CLAUDE.md` 비용 절·구조 절 `providers/`에 `RoutedProvider`·설정 이름 한 줄.
- 인수 팀이 먼저 재 볼 것(로드맵 0단계에 한 줄): 여러 모델로 나누기 전에 같은 모델에서 단계별 노력만 낮춘 경우와 비교한다(새 모델은 낮은 노력으로도 이전 세대 높은 노력에 맞먹는 경우가 많다). 설정은 노력만 바꾸는 것도 지원한다.
- HANDOFF·README·WBS: 기존 규칙대로.

## 5. 테스트

- `stage_targets`: 비어 있으면 빈 결과, 모델만·노력만·둘 다, 기본과 같은 단계는 빠짐.
- 설정 검증: 없는 단계 이름(`"generat"`, `"image"`)과 잘못된 노력 값이 `Settings(...)` 생성에서 실패. 올바른 JSON 환경 변수를 읽음.
- `RoutedProvider`: 정한 단계는 그 제공자, 나머지는 기본으로 간다(가짜 제공자로 호출 기록 확인).
- `get_provider`: mock이면 단계 설정과 상관없이 MockProvider. claude + 설정 없음이면 `ClaudeProvider`(감싸지 않음). claude + 설정이면 `RoutedProvider`이고 같은 (모델, 노력)은 같은 객체.
- 실제 요청 본문: `ClaudeProvider`에 SDK 클라이언트 + MockTransport를 주입하는 기존 테스트 방식(`tests/test_claude_provider.py`)으로, 라우팅된 두 단계의 요청 `model`·`output_config.effort`가 각각 설정대로인지 확인한다. Haiku 단계에는 `fallbacks`가 없다.
- 기존 테스트 전부 그대로 통과(기본값 꺼짐).

## 6. 이번에 하지 않는 것

- 과제별 라우팅(과제 정책에 단계 모델을 두기). 필요하면 정책에 같은 모양의 사전을 더해 설정 위에 덮는다.
- 실패 시 다른 모델로 넘기기(캐스케이드). 거절 대체는 이미 서버 쪽 `fallbacks`가 한다.
- 다른 종류의 제공자 섞기(오픈 모델 서버) — 로드맵 2단계.
- 실제 모델에서 Haiku 단계의 구조화 출력·품질 확인 — `scripts/claude_smoke.py`로 인수 팀이 확인한다.
