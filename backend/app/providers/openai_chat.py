"""GPT 제공자. 공식 SDK(openai)의 Chat Completions로 부르고, 결과와 오류를 LLMProvider 계약으로 바꾼다.

Chat Completions를 쓰는 까닭: 게이트웨이(BAZE 등)가 가장 넓게 지원하는 OpenAI 호환 경로다.
prompt.system은 system 메시지, prompt.user는 user 메시지다. 출력 구조는 response_model의 JSON Schema를
strict 모드로 강제한다. 키·주소는 인자로 받고, 없으면 SDK가 환경 변수 OPENAI_API_KEY·OPENAI_BASE_URL을 읽는다.

SDK의 chat.completions.parse를 쓰지 않는다. parse는 스키마 이름에 모델 이름을 그대로 써서
제네릭(`TaskResult[...]`)이 이름 규칙(^[a-zA-Z0-9_-]+$)에 걸려 400이 나고, 거절·잘림 처리를 ClaudeProvider와
같게 맞추기 어렵다. 그래서 create로 받고 finish_reason을 먼저 본 뒤 글을 검증한다.
"""
import os
import re
from typing import Any

import openai
from openai.lib._pydantic import to_strict_json_schema  # parse가 쓰는 변환(strict 규칙: 모든 속성 required 등)
from pydantic import BaseModel, ValidationError

from app.providers.base import Prompt, ProviderError, ProviderOutputError, ProviderResponse, Usage

MAX_COMPLETION_TOKENS = 16000  # 생각 토큰 포함 상한. ClaudeProvider의 MAX_TOKENS와 같은 크기
KEY_ENV_VAR = "OPENAI_API_KEY"


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        model: str,
        effort: str,
        client: Any | None = None,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.effort = effort
        if client is None and not (api_key or os.environ.get(KEY_ENV_VAR)):
            # 키 없이 만들면 SDK가 만들 때 실패한다. 무엇을 넣어야 하는지 알린다(키 값은 싣지 않는다).
            raise ValueError(
                "PROVIDER=openai인데 API 키가 없습니다. 환경 변수나 backend/.env에 OPENAI_API_KEY를 넣으세요."
            )
        self.client = client if client is not None else openai.OpenAI(base_url=base_url, api_key=api_key)

    def _request(self, prompt: Prompt, response_model: type[BaseModel] | None) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "reasoning_effort": self.effort,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
        }
        if response_model is not None:
            request["response_format"] = response_format(response_model)
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
            response = self.client.chat.completions.create(**self._request(prompt, response_model))
        except openai.APIError as exc:
            raise ProviderError(f"{stage} 단계 GPT 호출 실패: {type(exc).__name__}") from exc
        return _to_response(stage, response, response_model)


def response_format(response_model: type[BaseModel]) -> dict[str, Any]:
    """[순수] strict JSON Schema 응답 형식. 이름은 OpenAI 규칙(영숫자·_·-, 64자)에 맞춘다."""
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", response_model.__name__).strip("_")[:64] or "response"
    return {
        "type": "json_schema",
        "json_schema": {"name": name, "schema": to_strict_json_schema(response_model), "strict": True},
    }


def _to_response(stage: str, response: Any, response_model: type[BaseModel] | None) -> ProviderResponse:
    """[순수] SDK 응답을 계약의 응답으로. 거절·내용 필터는 호출 실패(다시 불러도 같다), 잘림은 스키마
    실패다(하네스가 한 번 더 부른다). 그다음 글을 검증한다."""
    choice = response.choices[0]
    if choice.message.refusal or choice.finish_reason == "content_filter":
        raise ProviderError(f"{stage} 단계 요청을 GPT가 거절했습니다.")
    if choice.finish_reason == "length":
        raise ProviderOutputError(f"{stage} 단계 응답이 길이 상한에서 잘렸습니다.")
    text = choice.message.content or ""
    parsed = None
    if response_model is not None:
        try:
            parsed = response_model.model_validate_json(text)
        except ValidationError as exc:
            raise ProviderOutputError(
                f"{stage} 단계 응답이 스키마를 통과하지 못했습니다: {exc.error_count()}개 오류"
            ) from exc
    return ProviderResponse(text=text, model=response.model, parsed=parsed, usage=_usage(response.usage))


def _usage(usage: Any) -> Usage:
    """[순수] OpenAI의 prompt_tokens는 캐시 읽기를 포함한다. 계약(Claude와 같게)은 캐시를 뺀 입력이다.
    OpenAI는 캐시 쓰기를 따로 세지 않는다."""
    if usage is None:
        return Usage(input_tokens=0, output_tokens=0)
    details = getattr(usage, "prompt_tokens_details", None)
    cached = (getattr(details, "cached_tokens", None) or 0) if details else 0
    return Usage(
        input_tokens=usage.prompt_tokens - cached,
        output_tokens=usage.completion_tokens,
        cache_read_input_tokens=cached,
    )
