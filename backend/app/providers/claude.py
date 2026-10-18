"""실제 Claude 제공자. 공식 SDK(anthropic)로 부르고, 결과와 오류를 LLMProvider 계약으로 바꾼다.

prompt.system은 과제마다 고정이라 캐시되는 시스템 블록, prompt.user는 사용자 메시지다. 출력 구조는
response_model의 JSON Schema로 강제한다(구조화 출력, output_config.format). 키는 환경 변수
ANTHROPIC_API_KEY(또는 ANTHROPIC_AUTH_TOKEN)에서 SDK가 읽는다.

SDK의 messages.parse를 쓰지 않는다. parse는 stop_reason을 보기 전에 글을 스키마로 검증해, 거절·잘림이
스키마 실패(ProviderOutputError → 하네스가 한 번 더 부름)로 바뀌고 대체 모델이 이어 쓴 응답의 앞 조각에서
실패한다. 그래서 create로 받고 stop_reason을 먼저 본 뒤 마지막 글 블록을 검증한다.
"""
import os
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from app.providers.base import Prompt, ProviderError, ProviderOutputError, ProviderResponse, Usage

MAX_TOKENS = 16000  # 비스트리밍 요청의 기본 상한(HTTP 시간 제한 안쪽)
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # 거절되면 서버가 권장 모델로 다시 돌린다
KEY_ENV_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str, effort: str, client: Any | None = None) -> None:
        self.model = model
        self.effort = effort
        if client is None and not any(os.environ.get(name) for name in KEY_ENV_VARS):
            # 키 없이 만들면 요청 때 TypeError(500)로 터진다. 서버 시작 때 바로 알린다(키 값은 싣지 않는다).
            raise ValueError(
                "PROVIDER=claude인데 API 키가 없습니다. 환경 변수나 backend/.env에 ANTHROPIC_API_KEY를 넣으세요."
            )
        self.client = client if client is not None else anthropic.Anthropic()

    def _request(self, prompt: Prompt, response_model: type[BaseModel] | None) -> dict[str, Any]:
        output_config: dict[str, Any] = {"effort": self.effort}
        if response_model is not None:
            output_config["format"] = {"type": "json_schema", "schema": anthropic.transform_schema(response_model)}
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": prompt.user}],
            "output_config": output_config,
        }
        if _supports_fallbacks(self.model):
            request["betas"] = [FALLBACK_BETA]
            request["fallbacks"] = "default"
        return request

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: Prompt,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        try:
            response = self.client.beta.messages.create(**self._request(prompt, response_model))
        except anthropic.APIError as exc:
            raise ProviderError(f"{stage} 단계 Claude 호출 실패: {type(exc).__name__}") from exc
        return _to_response(stage, response, response_model)


def _supports_fallbacks(model: str) -> bool:
    """[순수] 서버 측 대체 모델(fallbacks)을 붙일 모델인가. Haiku 요청에는 붙이지 않는다."""
    return not model.startswith("claude-haiku")


def _to_response(stage: str, response: Any, response_model: type[BaseModel] | None) -> ProviderResponse:
    """[순수] SDK 응답을 계약의 응답으로. stop_reason을 먼저 본다: 거절은 호출 실패(다시 불러도 같다),
    잘림은 스키마 실패다. 그다음 마지막 글 블록을 검증한다(대체 모델이 이어 쓰면 앞 조각·fallback 블록 뒤에
    완성된 글이 온다)."""
    if response.stop_reason == "refusal":
        raise ProviderError(f"{stage} 단계 요청을 Claude가 거절했습니다.")
    if response.stop_reason == "max_tokens":
        raise ProviderOutputError(f"{stage} 단계 응답이 길이 상한에서 잘렸습니다.")
    texts = [block.text for block in response.content if block.type == "text"]
    text = texts[-1] if texts else ""
    parsed = None
    if response_model is not None:
        try:
            parsed = response_model.model_validate_json(text)
        except ValidationError as exc:
            raise ProviderOutputError(
                f"{stage} 단계 응답이 스키마를 통과하지 못했습니다: {exc.error_count()}개 오류"
            ) from exc
    return ProviderResponse(
        text=text,
        model=response.model,
        parsed=parsed,
        # 대체 모델이 돌았으면 맨 위 usage는 마지막 시도 몫만이다(시도별 내역은 usage.iterations).
        usage=Usage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens),
    )
