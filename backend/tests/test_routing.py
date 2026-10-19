import anthropic
import httpx2 as httpx
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderResponse
from app.providers.claude import ClaudeProvider
from app.providers.factory import get_provider
from app.providers.mock import MockProvider
from app.providers.routing import ROUTABLE_STAGES, RoutedProvider, stage_targets

PROMPT = Prompt(system="고정", user="맥락")


def test_routable_stages_exclude_image():
    assert ROUTABLE_STAGES == ("diagnose", "easier_question", "propose_value", "generate", "validate")


def test_stage_targets_empty_settings_route_nothing():
    assert stage_targets("claude-opus-5-5", "medium", {}, {}) == {}


def test_stage_targets_fill_missing_half_with_default():
    targets = stage_targets(
        "claude-opus-5-5", "medium",
        {"diagnose": "claude-haiku-5-5", "generate": "claude-opus-5-5"},
        {"generate": "high", "validate": "medium"},
    )
    assert targets == {"diagnose": ("claude-haiku-5-5", "medium"), "generate": ("claude-opus-5-5", "high")}
    # validate는 기본과 같으므로 빠진다


class Recorder:
    def __init__(self, name):
        self.name, self.stages = name, []

    def complete(self, *, task_type, stage, prompt, response_model=None):
        self.stages.append(stage)
        return ProviderResponse(text="", model=self.name)


def test_routed_provider_sends_each_stage_to_its_provider():
    default, light = Recorder("default"), Recorder("light")
    routed = RoutedProvider(default, {"diagnose": light})
    routed.complete(task_type="branding", stage="diagnose", prompt=PROMPT)
    routed.complete(task_type="branding", stage="generate", prompt=PROMPT)
    assert light.stages == ["diagnose"] and default.stages == ["generate"]
    assert routed.name == "default"


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_mock_ignores_stage_settings():
    provider = get_provider("mock", stage_models={"diagnose": "claude-haiku-5-5"})
    assert isinstance(provider, MockProvider)


def test_claude_without_stage_settings_is_not_wrapped(fake_key):
    assert isinstance(get_provider("claude"), ClaudeProvider)


def test_claude_with_stage_settings_routes_and_shares_same_targets(fake_key):
    provider = get_provider(
        "claude",
        model="claude-opus-5-5", effort="medium",
        stage_models={"diagnose": "claude-haiku-5-5", "easier_question": "claude-haiku-5-5"},
        stage_efforts={"generate": "high"},
    )
    assert isinstance(provider, RoutedProvider)
    routes = provider.routes
    assert routes["diagnose"] is routes["easier_question"]
    assert (routes["diagnose"].model, routes["diagnose"].effort) == ("claude-haiku-5-5", "medium")
    assert (routes["generate"].model, routes["generate"].effort) == ("claude-opus-5-5", "high")
    assert (provider.default.model, provider.default.effort) == ("claude-opus-5-5", "medium")


class Answer(BaseModel):
    text: str


def test_routed_requests_carry_stage_model_and_effort():
    """실제 SDK 클라이언트 + MockTransport로 요청 본문을 본다(네트워크·비용 없음)."""
    import json

    bodies = []

    def server(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "msg", "type": "message", "role": "assistant", "model": bodies[-1]["model"],
            "content": [{"type": "text", "text": '{"text": "ok"}'}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    def claude(model, effort):
        client = anthropic.Anthropic(api_key="test-key", http_client=httpx.Client(transport=httpx.MockTransport(server)), max_retries=0)
        return ClaudeProvider(model=model, effort=effort, client=client)

    routed = RoutedProvider(claude("claude-opus-5-5", "medium"), {"diagnose": claude("claude-haiku-5-5", "low")})
    routed.complete(task_type="branding", stage="diagnose", prompt=PROMPT, response_model=Answer)
    routed.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=Answer)
    haiku, opus = bodies
    assert (haiku["model"], haiku["output_config"]["effort"]) == ("claude-haiku-5-5", "low")
    assert "fallbacks" not in haiku
    assert (opus["model"], opus["output_config"]["effort"]) == ("claude-opus-5-5", "medium")
    assert opus["fallbacks"] == "default"


def test_routable_stages_match_harness_stages():
    from app.harness.prompting import STAGES

    assert set(ROUTABLE_STAGES) == set(STAGES) - {"image"}
