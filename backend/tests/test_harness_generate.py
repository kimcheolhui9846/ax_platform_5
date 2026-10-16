import pytest

from app.core.results import ValidationIssue
from app.core.state import Answer, AnswerType, Assumption, InfoSource, SessionStatus
from app.harness.base import GENERIC_GENERATION_ERROR
from app.harness.errors import GenerationFailed
from app.harness.evals import load_scenarios, run_scenario
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness


def test_generate_completes_with_validated_result(harness):
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert state.result.content["summary"] == "[mock] 요약"
    assert state.result.cards
    assert state.validation.passed
    assert [t.stage for t in state.trace[-2:]] == ["generate", "validate"]


def test_generate_drops_pending_question(harness):
    state = harness.start("향초")
    harness.generate(state)
    assert state.pending_question is None
    assert all(a.answer_type is not None for a in state.asked_questions)


def test_generate_failure_preserves_input_and_can_retry():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    state = harness.start("향초")

    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED
    assert state.error == GENERIC_GENERATION_ERROR
    assert "[mock]" not in state.error
    assert state.facts["idea"].value == "향초"
    assert "[mock]" in state.trace[-1].output["error"]

    harness.provider = MockProvider()
    harness.generate(state)
    assert state.status is SessionStatus.COMPLETED
    assert state.error is None


def test_schema_error_retried_once():
    provider = MockProvider(output_errors={"generate": 1})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert [s for _, s in provider.calls].count("generate") == 2


def test_schema_error_twice_fails():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(output_errors={"generate": 2}))
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED


def test_regenerate_clears_stale(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    harness.generate(state)
    harness.revise_answer(
        state,
        Answer(question_id=state.asked_questions[0].question.question_id, answer_type=AnswerType.FREE_TEXT, value="부모"),
    )
    assert state.result_stale

    harness.generate(state)
    assert not state.result_stale


def test_task_validators_run(provider):
    def always_error(state, result, policy):
        return [ValidationIssue(rule="always", message="항상 실패", severity="error")]

    class StrictHarness(SampleHarness):
        validators = [always_error]

    harness = StrictHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    harness.generate(state)
    assert not state.validation.passed
    assert state.status is SessionStatus.COMPLETED


def test_unmarked_assumption_is_flagged(harness):
    state = harness.start("향초")
    state.assumptions["customer"] = Assumption(value="30대", source=InfoSource.AI_ASSUMPTION)
    harness.generate(state)
    assert "assumptions_marked" in [i.rule for i in state.validation.issues]


def test_llm_validation_only_when_enabled(harness, provider):
    state = harness.start("향초")
    harness.generate(state)
    assert ("sample_task", "validate") not in provider.calls

    harness.policy.llm_validation = True
    harness.generate(state)
    assert ("sample_task", "validate") in provider.calls


def test_llm_validation_failure_becomes_warning():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"validate"}))
    harness.policy.llm_validation = True
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert "llm_review_unavailable" in [i.rule for i in state.validation.issues]


def test_sample_scenario_runs(harness):
    scenarios = load_scenarios(SAMPLE_TASK_DIR)
    assert [s.name for s in scenarios] == ["모르겠어요 한 번 후 직접 입력"]

    state = run_scenario(harness, scenarios[0])
    assert state.status is scenarios[0].expect_status
    assert state.facts["customer"].value == "집들이 가는 30대"
    assert state.facts["problem"].value == "선물 고르기가 어렵다"


# ── 추출한 도우미 ─────────────────────────────────────────


def test_to_generation_result_maps_parsed_fields():
    from app.core.results import TaskResult
    from app.harness.base import to_generation_result
    from tests.conftest import SampleContent

    parsed = TaskResult[SampleContent](
        cards=[], assumptions=[], full_text="본문", content=SampleContent(summary="요", actions=["a"])
    )
    result = to_generation_result(parsed)
    assert result.full_text == "본문"
    assert result.content == {"summary": "요", "actions": ["a"]}


def test_collect_issues_runs_every_validator(harness):
    from app.core.results import GenerationResult
    from app.core.state import SessionState
    from app.harness.validation import check_cards_present, collect_issues

    state = SessionState(task_type="sample_task", raw_input="x")
    result = GenerationResult(cards=[], full_text="", content={})
    issues = collect_issues(
        [check_cards_present, check_cards_present], state, result, harness.policy
    )
    assert [i.rule for i in issues] == ["cards_present", "cards_present"]


def test_scenario_answer_to_answer_maps_option_indexes():
    from app.core.state import Question, QuestionOption
    from app.harness.evals import ScenarioAnswer, build_answer

    question = Question(
        field="f", text="q", options=[QuestionOption(id="o1", label="a"), QuestionOption(id="o2", label="b")]
    )
    answer = build_answer(question, ScenarioAnswer(answer_type=AnswerType.OPTION, option_indexes=[1]))
    assert answer.question_id == question.question_id
    assert answer.option_ids == ["o2"]


# ── 실패 처리·보강 ────────────────────────────────────────


def test_validator_exception_fails_generation_and_keeps_pending_question(provider):
    def boom(state, result, policy):
        raise RuntimeError("secret internal detail")

    class BoomHarness(SampleHarness):
        validators = [boom]

    harness = BoomHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    pending = state.pending_question
    assert pending is not None

    with pytest.raises(GenerationFailed):
        harness.generate(state)

    assert state.status is SessionStatus.FAILED
    assert state.error
    assert "secret" not in state.error
    assert state.result is None
    assert state.pending_question == pending
    assert state.asked_questions[-1].answer_type is None
    assert "secret internal detail" in str(state.trace[-1].output)


def test_template_error_fails_generation_without_leaking(tmp_path):
    import shutil

    task_dir = tmp_path / "task"
    shutil.copytree(SAMPLE_TASK_DIR, task_dir)
    (task_dir / "prompts" / "generate.md").write_text("{{ nope.x }}", encoding="utf-8")
    harness = SampleHarness(task_dir, MockProvider())
    state = harness.start("향초")

    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED
    assert "nope" not in state.error


def test_can_answer_kept_question_after_failed_generate():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    state = harness.start("향초")
    question = state.pending_question
    with pytest.raises(GenerationFailed):
        harness.generate(state)

    harness.apply_answer(
        state,
        Answer(question_id=question.question_id, answer_type=AnswerType.FREE_TEXT, value="직접 답"),
    )
    assert state.facts[question.field].value == "직접 답"
    assert state.status is not SessionStatus.FAILED


def test_summary_trace_is_distinguishable_from_llm_review_trace(harness):
    harness.policy.llm_validation = True
    state = harness.start("향초")
    harness.generate(state)
    validate_entries = [t for t in state.trace if t.stage == "validate"]
    assert len(validate_entries) == 2
    assert [t.output.get("kind") for t in validate_entries] == [None, "summary"]


def test_build_answer_rejects_out_of_range_option_index():
    from app.core.state import Question, QuestionOption
    from app.harness.evals import ScenarioAnswer, build_answer

    question = Question(field="customer", text="q", options=[QuestionOption(id="o1", label="a")])
    with pytest.raises(ValueError, match="customer.*5"):
        build_answer(question, ScenarioAnswer(answer_type=AnswerType.OPTION, option_indexes=[5]))


def test_scenario_mode_and_expect_status_are_honored(harness):
    from app.core.state import CoachingMode
    from app.harness.evals import Scenario

    scenario = Scenario(
        name="빠른 모드", raw_input="향초", mode=CoachingMode.QUICK, expect_status=SessionStatus.COMPLETED
    )
    state = run_scenario(harness, scenario)
    assert state.mode is CoachingMode.QUICK
    assert state.status is scenario.expect_status
