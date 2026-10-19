"""evals 시나리오 형식과 실행기의 엄격한 검사."""
import pytest
from pydantic import ValidationError

from app.core.state import AnswerType, SessionStatus
from app.harness.evals import Scenario, ScenarioAnswer, run_scenario
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness


def test_scenario_typo_rejected():
    with pytest.raises(ValidationError, match="expect_staus"):
        Scenario.model_validate({"name": "s", "raw_input": "향초", "expect_staus": "completed"})


def test_scenario_answer_typo_rejected():
    with pytest.raises(ValidationError, match="option_index"):
        ScenarioAnswer.model_validate({"answer_type": "option", "option_index": [0]})


def test_unknown_answers_key_fails_with_scenario_name(harness):
    scenario = Scenario(name="오타 시나리오", raw_input="향초", answers={"custmer": [ScenarioAnswer(value="부모")]})
    with pytest.raises(ValueError, match="오타 시나리오.*custmer"):
        run_scenario(harness, scenario)


def test_default_field_answers_key_fails(harness):
    """kind=default 필드는 묻지 않으므로 답을 계획할 수 없다."""
    scenario = Scenario(name="기본값 시나리오", raw_input="향초", answers={"length": [ScenarioAnswer(value="짧게")]})
    with pytest.raises(ValueError, match="기본값 시나리오.*length"):
        run_scenario(harness, scenario)


def test_leftover_answers_fail_with_scenario_name(harness):
    scenario = Scenario(
        name="남는 답 시나리오",
        raw_input="향초",
        answers={
            "customer": [
                ScenarioAnswer(value="부모"),
                ScenarioAnswer(answer_type=AnswerType.EASIER),
            ]
        },
    )
    with pytest.raises(ValueError, match="남는 답 시나리오.*customer"):
        run_scenario(harness, scenario)



def test_bad_option_index_error_names_scenario_and_field(harness):
    scenario = Scenario(
        name="범위 밖 시나리오",
        raw_input="향초",
        answers={"customer": [ScenarioAnswer(answer_type=AnswerType.OPTION, option_indexes=[9])]},
    )
    with pytest.raises(ValueError, match="범위 밖 시나리오.*customer"):
        run_scenario(harness, scenario)


def test_failed_generation_scenario_returns_state():
    """expect_status: failed 시나리오를 쓸 수 있다. 생성 실패는 예외가 아니라 결과 상태로 돌려준다."""
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    scenario = Scenario.model_validate(
        {"name": "생성 실패", "raw_input": "향초", "expect_status": "failed"}
    )
    state = run_scenario(harness, scenario)
    assert state.status is scenario.expect_status is SessionStatus.FAILED
    assert state.result is None


def test_play_questions_reports_mismatches_instead_of_failing(harness):
    """실제 모델은 질문 순서가 달라 계획이 어긋날 수 있다. 측정에서는 어긋남을 지표로 받는다."""
    from app.harness.evals import play_questions

    scenario = Scenario(
        name="어긋나는 시나리오",
        raw_input="향초",
        answers={
            "customer": [
                ScenarioAnswer(answer_type=AnswerType.OPTION, option_indexes=[9]),
                ScenarioAnswer(value="남는 답"),
            ]
        },
    )
    played = play_questions(harness, scenario)
    assert played.state.pending_question is None
    assert len(played.mismatches) == 2
    assert "customer" in played.mismatches[0] and "customer" in played.mismatches[1]
