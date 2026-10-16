from pathlib import Path

import pytest
import yaml
from jinja2 import UndefinedError
from pydantic import ValidationError

from app.core.state import (
    SOURCE_LABELS,
    Assumption,
    CoachingMode,
    InfoItem,
    InfoSource,
    SessionState,
    source_label,
)
from app.harness.policy import FieldKind, load_policy
from app.harness.prompting import STAGES, PromptContextError, PromptRenderer, context_keys

SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_task"


def write_policy(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def base_policy(**overrides) -> dict:
    data = {
        "task_type": "t",
        "title": "t",
        "fields": [{"name": "a", "label": "에이", "question": "에이는?"}],
    }
    data.update(overrides)
    return data


def test_load_sample_policy():
    policy = load_policy(SAMPLE_DIR / "policy.yaml")
    assert [f.name for f in policy.fields] == ["idea", "customer", "problem", "tone", "length"]
    assert policy.field("length").kind is FieldKind.DEFAULT
    assert policy.question_caps[CoachingMode.QUICK] == 2
    assert policy.labels["customer"] == "목표 고객"
    assert policy.llm_validation is False


def test_default_caps_when_omitted(tmp_path):
    policy = load_policy(write_policy(tmp_path, base_policy()))
    assert policy.question_caps == {
        CoachingMode.QUICK: 3,
        CoachingMode.STANDARD: 5,
        CoachingMode.PRECISE: 10,
    }


def test_duplicate_field_names_rejected(tmp_path):
    fields = [{"name": "a", "label": "에이", "question": "?"}] * 2
    with pytest.raises(ValidationError, match="중복"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


def test_default_kind_requires_default_value(tmp_path):
    fields = [{"name": "a", "label": "에이", "kind": "default"}]
    with pytest.raises(ValidationError, match="default"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


def test_unknown_raw_input_field_rejected(tmp_path):
    with pytest.raises(ValidationError, match="raw_input_field"):
        load_policy(write_policy(tmp_path, base_policy(raw_input_field="nope")))


def test_partial_question_caps_rejected(tmp_path):
    with pytest.raises(ValidationError, match="question_caps"):
        load_policy(write_policy(tmp_path, base_policy(question_caps={"standard": 5})))


def sample_values() -> dict:
    """모든 단계 변수의 표본 값. 단계마다 context_keys(stage)만 골라 넘긴다."""
    policy = load_policy(SAMPLE_DIR / "policy.yaml")
    state = SessionState(task_type="sample_task", raw_input="집들이 선물용 향초")
    state.facts["idea"] = InfoItem(value="향초", source=InfoSource.USER_FREE_TEXT)
    return {
        "state": state,
        "policy": policy,
        "profile": state.profile,
        "field": policy.field("customer"),
        "level": 3,
        "previous": ["이전 질문"],
        "result_text": "결과 본문",
    }


def sample_context(stage: str) -> dict:
    values = sample_values()
    return {key: values[key] for key in context_keys(stage)}


@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_renders(stage):
    prompt = PromptRenderer(SAMPLE_DIR / "prompts").render(stage, **sample_context(stage))
    assert "집들이 선물용 향초" in prompt.user
    assert "idea (아이디어): 향초" in prompt.user


def test_task_template_overrides_common_and_keeps_base():
    system = PromptRenderer(SAMPLE_DIR / "prompts").render("generate", **sample_context("generate")).system
    assert "샘플 지침 문구" in system
    assert "근거 없는 숫자를 사실처럼 쓰지 않는다" in system


def test_missing_task_template_falls_back_to_common(tmp_path):
    system = PromptRenderer(tmp_path / "prompts").render("generate", **sample_context("generate")).system
    assert "샘플 지침 문구" not in system
    assert "지켜야 할 규칙" in system


# ── 엄격한 정책 검증: 오타·잘못된 값은 읽을 때 바로 거부한다 ─────────


def test_policy_typo_rejected(tmp_path):
    with pytest.raises(ValidationError, match="readiness_treshold"):
        load_policy(write_policy(tmp_path, base_policy(readiness_treshold=0.5)))


def test_field_typo_rejected(tmp_path):
    fields = [{"name": "a", "label": "에이", "question": "?", "multi-select": True}]
    with pytest.raises(ValidationError, match="multi-select"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


def test_ladder_step_typo_rejected(tmp_path):
    fields = [{"name": "a", "label": "에이", "question": "?", "easier_questions": [{"question": "쉬운?", "option": ["가"]}]}]
    with pytest.raises(ValidationError, match="option"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


@pytest.mark.parametrize("cap", [0, -1])
def test_non_positive_question_cap_rejected(tmp_path, cap):
    caps = {"quick": cap, "standard": 5, "precise": 10}
    with pytest.raises(ValidationError, match="greater than 0"):
        load_policy(write_policy(tmp_path, base_policy(question_caps=caps)))


def test_unreachable_ladder_step_rejected(tmp_path):
    """max_easier_level 단계부터는 AI 후보 제안이 대신하므로 그 이상의 사다리 질문은 닿지 않는다."""
    steps = [{"question": f"쉬운 질문 {i}"} for i in range(2)]
    fields = [{"name": "a", "label": "에이", "question": "?", "easier_questions": steps}]
    with pytest.raises(ValidationError, match="easier_questions"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields, max_easier_level=2)))


def test_ladder_just_below_max_level_is_allowed(tmp_path):
    steps = [{"question": f"쉬운 질문 {i}"} for i in range(1)]
    fields = [{"name": "a", "label": "에이", "question": "?", "easier_questions": steps}]
    policy = load_policy(write_policy(tmp_path, base_policy(fields=fields, max_easier_level=2)))
    assert len(policy.field("a").easier_questions) == 1


# ── 단계별 프롬프트 변수: 단계마다 정해진 키만 넘기고 쓴다 ─────────────


def test_stage_context_declares_specific_keys():
    assert context_keys("diagnose") == {"state", "policy", "profile"}
    assert context_keys("easier_question") == {"state", "policy", "profile", "field", "level", "previous"}
    assert context_keys("generate") == {"state", "policy", "profile"}
    assert context_keys("validate") == {"state", "policy", "profile", "result_text"}


def test_render_rejects_unexpected_key():
    context = {**sample_context("diagnose"), "level": 3}
    with pytest.raises(PromptContextError, match="level"):
        PromptRenderer(SAMPLE_DIR / "prompts").render("diagnose", **context)


def test_render_rejects_missing_key():
    context = sample_context("validate")
    del context["result_text"]
    with pytest.raises(PromptContextError, match="result_text"):
        PromptRenderer(SAMPLE_DIR / "prompts").render("validate", **context)


def test_render_rejects_unknown_stage():
    with pytest.raises(PromptContextError, match="nope"):
        PromptRenderer(SAMPLE_DIR / "prompts").render("nope", **sample_context("diagnose"))


def test_template_using_another_stage_variable_fails(tmp_path):
    """diagnose 템플릿이 쉬운 질문 단계의 변수(field)를 쓰면 정해진 키만으로는 렌더링되지 않는다."""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "diagnose.md").write_text("{{ field.label }}", encoding="utf-8")
    with pytest.raises(UndefinedError, match="field"):
        PromptRenderer(prompts).render("diagnose", **sample_context("diagnose"))


# ── 필드 식별자: 프롬프트는 내부 이름과 라벨을 함께 보여 준다 ─────────


def test_context_shows_field_name_and_label():
    context = sample_context("diagnose")
    context["state"].assumptions["customer"] = Assumption(value="30대", source=InfoSource.AI_ASSUMPTION)
    context["state"].unknowns.append("problem")
    text = PromptRenderer(SAMPLE_DIR / "prompts").render("diagnose", **context).user
    assert "- idea (아이디어): 향초" in text
    assert "- customer (목표 고객): 30대" in text
    assert "- problem (고객 문제)" in text


def test_generate_prompt_lists_allowed_assumption_fields():
    text = PromptRenderer(SAMPLE_DIR / "prompts").render("generate", **sample_context("generate")).system
    assert "idea, customer, problem, tone, length" in text



# ── 템플릿 모양: 빈 줄 두 개 연속 없음, 출처는 한국어 라벨(#9) ──────


@pytest.mark.parametrize("stage", STAGES)
def test_rendered_prompt_has_no_double_blank_lines(stage):
    context = sample_context(stage)
    context["state"].unknowns.append("problem")
    prompt = PromptRenderer(SAMPLE_DIR / "prompts").render(stage, **context)
    assert "\n\n\n" not in prompt.system
    assert "\n\n\n" not in prompt.user


def test_context_shows_source_as_korean_label():
    text = PromptRenderer(SAMPLE_DIR / "prompts").render("diagnose", **sample_context("diagnose")).user
    assert "(출처: 직접 입력)" in text
    assert "user_free_text" not in text


def test_source_labels_cover_every_source():
    assert set(SOURCE_LABELS) == set(InfoSource)
    assert source_label(InfoSource.AI_ASSUMPTION) == "AI 가정"



# ── 시스템/사용자 분리: 과제 고정 내용은 system, 세션 맥락은 user(캐시 가능한 앞부분) ──


@pytest.mark.parametrize("stage", STAGES)
def test_prompt_splits_static_system_from_session_user(stage):
    prompt = PromptRenderer(SAMPLE_DIR / "prompts").render(stage, **sample_context(stage))
    assert prompt.system.strip() and prompt.user.strip()
    assert "샘플 과제" in prompt.system
    assert "집들이 선물용 향초" not in prompt.system  # raw_input
    assert "idea (아이디어): 향초" not in prompt.system  # facts


def test_generate_prompt_has_no_json_schema():
    """출력 구조는 제공자가 response_model로 강제한다. 프롬프트에 스키마를 싣지 않는다."""
    prompt = PromptRenderer(SAMPLE_DIR / "prompts").render("generate", **sample_context("generate"))
    for part in (prompt.system, prompt.user):
        assert "JSON Schema" not in part
        assert '"properties"' not in part
