import pytest

from app.core.results import GenerationResult, ResultCard
from app.core.state import SessionState
from app.harness.errors import UnknownTaskError
from app.harness.evals import load_scenarios, run_scenario
from app.harness.policy import FieldKind
from app.harness.prompting import STAGES
from app.harness.registry import TASK_TYPES, TASKS_DIR, HarnessRegistry
from app.harness.tasks.business_plan.validators import check_unsupported_market_claims
from app.harness.tasks.marketing_content.validators import check_cta_present
from app.harness.validation import find_terms
from app.providers.mock import MockProvider


@pytest.fixture(scope="module")
def registry():
    return HarnessRegistry(MockProvider())


def test_registry_has_all_tasks(registry):
    assert [h.task_type for h in registry.all()] == list(TASK_TYPES)
    with pytest.raises(UnknownTaskError):
        registry.get("nope")


@pytest.mark.parametrize("task_type", TASK_TYPES)
def test_policy_is_complete(registry, task_type):
    policy = registry.get(task_type).policy
    assert policy.task_type == task_type
    assert policy.raw_input_field is not None
    assert policy.rules
    for field in policy.fields:
        if field.kind is FieldKind.MUST_CONFIRM:
            assert field.easier_questions, f"{field.name}: 반드시 확인 필드에는 쉬운 질문이 하나 이상 필요"


@pytest.mark.parametrize("task_type", TASK_TYPES)
@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_template_renders(registry, task_type, stage):
    harness = registry.get(task_type)
    state = harness.start("테스트 입력")
    text = harness.prompts.render(
        stage,
        state=state,
        policy=harness.policy,
        profile=state.profile,
        field=harness.policy.fields[0],
        level=3,
        previous=[],
        output_schema="{}",
        result_text="결과",
    )
    assert "테스트 입력" in text


@pytest.mark.parametrize("task_type", TASK_TYPES)
def test_eval_scenarios_complete(registry, task_type):
    harness = registry.get(task_type)
    scenarios = load_scenarios(TASKS_DIR / task_type)
    assert scenarios
    for scenario in scenarios:
        state = run_scenario(harness, scenario)
        assert state.status is scenario.expect_status, scenario.name
        harness.content_model.model_validate(state.result.content)


def make_result(full_text: str = "본문", content: dict | None = None) -> GenerationResult:
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    return GenerationResult(cards=[card], full_text=full_text, content=content or {})


def test_business_plan_flags_market_claims(registry):
    policy = registry.get("business_plan").policy
    state = SessionState(task_type="business_plan")
    assert check_unsupported_market_claims(state, make_result("시장 규모는 1조 원"), policy)
    assert not check_unsupported_market_claims(state, make_result("고객 인터뷰부터"), policy)


def test_marketing_requires_cta(registry):
    policy = registry.get("marketing_content").policy
    state = SessionState(task_type="marketing_content")
    issues = check_cta_present(state, make_result(content={"cta": "  "}), policy)
    assert issues and issues[0].severity == "error"
    assert not check_cta_present(state, make_result(content={"cta": "프로필 링크에서 구매"}), policy)


def test_find_terms_returns_only_present_terms_in_order():
    assert find_terms("무조건 100% 보장", ("100%", "완벽", "무조건")) == ["100%", "무조건"]
    assert find_terms("평범한 문장", ("100%",)) == []
