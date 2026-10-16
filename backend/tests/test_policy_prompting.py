from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.core.state import CoachingMode, InfoItem, InfoSource, SessionState
from app.harness.policy import FieldKind, load_policy
from app.harness.prompting import STAGES, PromptRenderer

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


def sample_context() -> dict:
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
        "output_schema": "{}",
        "result_text": "결과 본문",
    }


@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_renders(stage):
    text = PromptRenderer(SAMPLE_DIR / "prompts").render(stage, **sample_context())
    assert "집들이 선물용 향초" in text
    assert "아이디어: 향초" in text


def test_task_template_overrides_common_and_keeps_base():
    text = PromptRenderer(SAMPLE_DIR / "prompts").render("generate", **sample_context())
    assert "샘플 지침 문구" in text
    assert "근거 없는 숫자를 사실처럼 쓰지 않는다" in text


def test_missing_task_template_falls_back_to_common(tmp_path):
    text = PromptRenderer(tmp_path / "prompts").render("generate", **sample_context())
    assert "샘플 지침 문구" not in text
    assert "출력 형식" in text


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
