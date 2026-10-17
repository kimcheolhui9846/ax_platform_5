import pytest

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import CoachingMode, SessionState
from app.harness.errors import UnknownTaskError
from app.harness.evals import load_scenarios, run_scenario
from app.harness.policy import FieldKind
from app.harness.prompting import STAGES, context_keys
from app.harness.registry import TASK_TYPES, TASKS_DIR, HarnessRegistry, build_harness
from app.harness.tasks.business_plan.validators import check_unsupported_market_claims
from app.harness.tasks.branding.validators import check_naming_not_definitive
from app.harness.tasks.marketing_content.validators import check_cta_present, check_no_exaggeration
from app.harness.tasks.product_planning.validators import MAX_CORE_FEATURES, check_mvp_not_too_big
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
    """단계마다 STAGE_CONTEXT에 선언된 키만 넘긴다. 다른 단계 변수를 쓰는 템플릿은 여기서 실패한다."""
    harness = registry.get(task_type)
    state = harness.start("테스트 입력")
    values = {
        "state": state,
        "policy": harness.policy,
        "profile": state.profile,
        "field": harness.policy.fields[0],
        "level": 3,
        "previous": [],
        "result_text": "결과",
        "heading": "섹션 제목",
        "text": "섹션 본문",
    }
    prompt = harness.prompts.render(stage, **{key: values[key] for key in context_keys(stage)})
    assert prompt.system.strip() and prompt.user.strip()
    assert "테스트 입력" in prompt.user
    assert "테스트 입력" not in prompt.system
    assert harness.policy.title in prompt.system
    for part in (prompt.system, prompt.user):
        assert "\n\n\n" not in part


@pytest.mark.parametrize("task_type", TASK_TYPES)
def test_eval_scenarios_complete(registry, task_type):
    harness = registry.get(task_type)
    scenarios = load_scenarios(TASKS_DIR / task_type)
    assert scenarios
    for scenario in scenarios:
        state = run_scenario(harness, scenario)
        assert state.status is scenario.expect_status, scenario.name
        if state.result is not None:
            harness.content_model.model_validate(state.result.content)


def make_result(full_text: str = "본문", content: dict | None = None) -> GenerationResult:
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    return GenerationResult(sections=sections_from_cards([card]), full_text=full_text, content=content or {})


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


def test_build_harness_rejects_unregistered_task_type():
    with pytest.raises(UnknownTaskError):
        build_harness("../etc", MockProvider())
    with pytest.raises(UnknownTaskError):
        build_harness("nope", MockProvider())


def test_marketing_flags_exaggeration(registry):
    policy = registry.get("marketing_content").policy
    state = SessionState(task_type="marketing_content")
    assert check_no_exaggeration(state, make_result("무조건 100% 만족"), policy)
    assert not check_no_exaggeration(state, make_result("겨울밤에 어울리는 향"), policy)


def test_branding_flags_definitive_naming(registry):
    policy = registry.get("branding").policy
    state = SessionState(task_type="branding")
    assert check_naming_not_definitive(state, make_result("이 이름으로 확정하세요"), policy)
    assert not check_naming_not_definitive(state, make_result("이름 후보와 상표 확인 과제"), policy)


def test_product_planning_mvp_size_boundary(registry):
    policy = registry.get("product_planning").policy
    state = SessionState(task_type="product_planning")

    def features(count: int) -> GenerationResult:
        return make_result(content={"core_features": [f"기능{i}" for i in range(count)]})

    assert not check_mvp_not_too_big(state, features(MAX_CORE_FEATURES), policy)
    assert check_mvp_not_too_big(state, features(MAX_CORE_FEATURES + 1), policy)



def test_every_task_folder_is_registered_and_vice_versa():
    """폴더만 만들고 TASK_TYPES에 빠뜨리거나, 등록만 하고 폴더가 없으면 여기서 걸린다."""
    folders = {p.parent.name for p in TASKS_DIR.glob("*/harness.py")}
    assert folders == set(TASK_TYPES)


def test_term_rule_builds_a_validator():
    from app.harness.validation import term_rule

    check = term_rule("demo", ("가", "나"), "표현이 있습니다: {terms}")
    state = SessionState(task_type="x")
    policy = build_harness("branding", MockProvider()).policy
    [issue] = check(state, make_result("나 그리고 가"), policy)
    assert (issue.rule, issue.message, issue.severity) == ("demo", "표현이 있습니다: 가, 나", "warning")
    assert check(state, make_result("다"), policy) == []


def test_term_validators_keep_rule_names_and_messages(registry):
    state = SessionState(task_type="x")
    policy = registry.get("business_plan").policy
    [claim] = check_unsupported_market_claims(state, make_result("시장 규모와 예상 매출"), policy)
    assert claim.rule == "unsupported_market_claims"
    assert claim.message == "근거 확인이 필요한 표현이 있습니다: 시장 규모, 예상 매출. 출처가 없다면 가정으로 표시하세요."
    [naming] = check_naming_not_definitive(state, make_result("바로 사용하세요"), policy)
    assert (naming.rule, naming.message) == (
        "naming_not_definitive",
        "상표·도메인 검토 전에 이름을 확정적으로 권고하는 표현이 있습니다.",
    )
    [hype] = check_no_exaggeration(state, make_result("무조건 100%"), policy)
    assert (hype.rule, hype.message) == ("no_exaggeration", "과장 광고로 보일 수 있는 표현이 있습니다: 100%, 무조건")


@pytest.mark.parametrize("task_type", TASK_TYPES)
@pytest.mark.parametrize("stage", STAGES)
def test_system_prompt_is_identical_across_sessions(registry, task_type, stage):
    """system 부분은 과제마다 고정이라 캐시할 수 있어야 한다. 세션·호출마다 다른 값이 섞이면 실패한다."""
    from app.core.state import Assumption, InfoItem, InfoSource

    harness = registry.get(task_type)
    fields = harness.policy.fields
    first = harness.start("첫 번째 세션의 아이디어")
    second = harness.start("전혀 다른 두 번째 아이디어", mode=CoachingMode.PRECISE)
    second.facts[fields[1].name] = InfoItem(value="두 번째 세션만의 답", source=InfoSource.USER_SELECTED_AI_OPTION)
    second.assumptions[fields[2].name] = Assumption(value="두 번째 가정", source=InfoSource.AI_ASSUMPTION)
    second.unknowns.append(fields[3].name)
    second.profile.alternative_count = 5

    def render(state, field, level, previous, result_text):
        values = {
            "state": state,
            "policy": harness.policy,
            "profile": state.profile,
            "field": field,
            "level": level,
            "previous": previous,
            "result_text": result_text,
            "heading": result_text,
            "text": result_text,
        }
        return harness.prompts.render(stage, **{key: values[key] for key in context_keys(stage)})

    a = render(first, fields[0], 1, [], "첫 결과")
    b = render(second, fields[1], 3, ["이전 질문", "또 다른 질문"], "두 번째 결과")
    assert a.system == b.system
    assert a.user != b.user
