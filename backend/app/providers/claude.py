"""실제 Claude 제공자. 공식 SDK(anthropic)로 부르고, 결과와 오류를 LLMProvider 계약으로 바꾼다.

prompt.system은 과제마다 고정이라 캐시되는 시스템 블록, prompt.user는 사용자 메시지다. 출력 구조는
response_model로 강제한다(구조화 출력). 키는 환경 변수 ANTHROPIC_API_KEY에서 SDK가 읽는다.
"""
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from app.providers.base import Prompt, ProviderError, ProviderOutputError, ProviderResponse, Usage

MAX_TOKENS = 16000  # 비스트리밍 요청의 기본 상한(HTTP 시간 제한 안쪽)
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # 거절되면 서버가 권장 모델로 다시 돌린다


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str, effort: str, client: Any | None = None) -> None:
        self.model = model
        self.effort = effort
        self.client = client if client is not None else anthropic.Anthropic()

    def _request(self, prompt: Prompt) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": prompt.user}],
            "output_config": {"effort": self.effort},
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: Prompt,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        try:
            if response_model is None:
                response = self.client.beta.messages.create(**self._request(prompt))
            else:
                response = self.client.beta.messages.parse(**self._request(prompt), output_format=response_model)
        except ValidationError as exc:
            raise ProviderOutputError(f"{stage} 단계 응답이 스키마를 통과하지 못했습니다: {exc.error_count()}개 오류") from exc
        except anthropic.APIError as exc:
            raise ProviderError(f"{stage} 단계 Claude 호출 실패: {type(exc).__name__}") from exc
        return _to_response(stage, response, response_model)


def _to_response(stage: str, response: Any, response_model: type[BaseModel] | None) -> ProviderResponse:
    """[순수] SDK 응답을 계약의 응답으로. 거절은 호출 실패, 잘림·빈 구조화 출력은 스키마 실패다."""
    if response.stop_reason == "refusal":
        raise ProviderError(f"{stage} 단계 요청을 Claude가 거절했습니다.")
    if response.stop_reason == "max_tokens":
        raise ProviderOutputError(f"{stage} 단계 응답이 길이 상한에서 잘렸습니다.")
    parsed = getattr(response, "parsed_output", None) if response_model is not None else None
    if response_model is not None and parsed is None:
        raise ProviderOutputError(f"{stage} 단계 응답에 구조화된 결과가 없습니다.")
    text = next((block.text for block in response.content if block.type == "text"), "")
    return ProviderResponse(
        text=text,
        model=response.model,
        parsed=parsed,
        usage=Usage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens),
    )
