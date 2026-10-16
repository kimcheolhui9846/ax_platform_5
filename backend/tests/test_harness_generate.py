import pytest

from app.core.results import GenerationResult, ResultAssumption, ValidationIssue
from app.core.state import Answer, AnswerType, Assumption, InfoSource, SessionState, SessionStatus
from app.harness.base import merge_assumptions
from app.harness.errors import GenerationFailed
from app.harness.evals import load_scenarios, run_scenario
from app.harness.validation import check_assumptions_marked
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
    assert state.facts["idea"].value == "향초"
    assert "[mock]" in state.trace[-1].output["error"]

    harness.provider = MockProvider()
    harness.generate(state)
    assert state.status is SessionStatus.COMPLETED


def test_session_state_does_not_store_error():
    """사용자에게 보일 오류 문구는 상태(FAILED)에서 뷰가 만든다. 따로 저장하면 상태와 어긋난다."""
    assert "error" not in SessionState.model_fields


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


def test_generate_marks_session_assumptions_in_code(harness):
    """LLM이 가정을 다시 적어 주길 믿지 않는다. 세션 가정은 코드가 결과에 넣는다."""
    state = harness.start("향초")
    state.assumptions["customer"] = Assumption(
        value="30대", source=InfoSource.AI_ASSUMPTION, reason="처음 입력에서 추출"
    )
    harness.generate(state)
    marked = {a.field: a for a in state.result.assumptions}
    assert (marked["customer"].value, marked["customer"].reason) == ("30대", "처음 입력에서 추출")
    assert "assumptions_marked" not in [i.rule for i in state.validation.issues]


LABELS = {"customer": "목표 고객", "problem": "고객 문제"}


def test_merge_assumptions_adds_missing_session_assumptions():
    llm = [ResultAssumption(field="problem", value="LLM 값", reason="LLM 이유")]
    session = {
        "problem": Assumption(value="세션 값", source=InfoSource.AI_ASSUMPTION),
        "customer": Assumption(value="30대", source=InfoSource.AI_ASSUMPTION, reason=""),
    }
    merged = merge_assumptions(llm, session, LABELS)
    assert [(a.field, a.value) for a in merged] == [("problem", "LLM 값"), ("customer", "30대")]
    assert merged[1].reason  # 이유가 비어 있으면 기본 이유를 단다
    assert merged[1].requires_confirmation is True


def test_merge_assumptions_maps_label_to_field_name():
    """LLM이 field에 라벨을 적어도 같은 항목으로 본다(중복으로 다시 넣지 않는다)."""
    llm = [ResultAssumption(field="목표 고객", value="30대")]
    session = {"customer": Assumption(value="30대", source=InfoSource.AI_ASSUMPTION)}
    merged = merge_assumptions(llm, session, LABELS)
    assert [(a.field, a.value) for a in merged] == [("customer", "30대")]


def test_merge_assumptions_keeps_llm_only_items():
    llm = [ResultAssumption(field="extra", value="v")]
    assert [a.field for a in merge_assumptions(llm, {}, LABELS)] == ["extra"]


def test_assumptions_marked_flags_missing_and_accepts_label(harness):
    state = SessionState(task_type="sample_task")
    state.assumptions["customer"] = Assumption(value="30대", source=InfoSource.AI_ASSUMPTION)

    def result_with(field: str | None) -> GenerationResult:
        marked = [ResultAssumption(field=field, value="30대")] if field else []
        return GenerationResult(cards=[], assumptions=marked, full_text="", content={})

    assert [i.rule for i in check_assumptions_marked(state, result_with(None), harness.policy)] == [
        "assumptions_marked"
    ]
    assert not check_assumptions_marked(state, result_with("customer"), harness.policy)
    assert not check_assumptions_marked(state, result_with("목표 고객"), harness.policy)


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
    assert "nope" in str(state.trace[-1].output)


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
