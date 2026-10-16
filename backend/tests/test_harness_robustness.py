import pytest

from app.core.state import Answer, AnswerType, InfoSource
from app.harness.stage_models import Diagnosis, ExtractedField
from app.providers.base import ProviderError, ProviderOutputError, ProviderResponse
from app.providers.mock import MockProvider


class DiagnosisStub(MockProvider):
    def complete(self, *, task_type, stage, prompt, response_model=None):
        if stage == "diagnose":
            parsed = Diagnosis(extracted=[ExtractedField(field="customer", value="30대 직장인")])
            self.calls.append((task_type, stage))
            return ProviderResponse(text="{}", model="stub", parsed=parsed)
        return super().complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)


class NoParsedProvider(MockProvider):
    def complete(self, *, task_type, stage, prompt, response_model=None):
        self.calls.append((task_type, stage))
        return ProviderResponse(text="plain", model="stub", parsed=None)


def snapshot(state):
    return state.model_dump(exclude={"trace"})


def test_failed_provider_call_rolls_back_apply_answer(harness, provider, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.DONT_KNOW)
    reply(harness, state, AnswerType.DONT_KNOW)
    before = snapshot(state)
    pending_id = state.pending_question.question_id
    provider.fail_stages.add("easier_question")

    with pytest.raises(ProviderError):
        reply(harness, state, AnswerType.DONT_KNOW)

    assert snapshot(state) == before
    assert state.pending_question.question_id == pending_id
    assert state.dont_know_levels == {"customer": 2}
    assert state.asked_questions[-1].answer_type is None
    assert state.trace[-1].stage == "easier_question"
    assert "error" in state.trace[-1].output

    provider.fail_stages.clear()
    reply(harness, state, AnswerType.DONT_KNOW)
    assert state.pending_question.level == 3


def test_failed_revise_rolls_back(harness, reply, monkeypatch):
    state = harness.start("향초")
    reply(harness, state, AnswerType.DONT_KNOW)
    before = snapshot(state)
    question_id = state.asked_questions[0].question.question_id

    def boom(_state):
        raise ProviderError("boom")

    monkeypatch.setattr(harness, "advance", boom)
    with pytest.raises(ProviderError):
        harness.revise_answer(
            state, Answer(question_id=question_id, answer_type=AnswerType.FREE_TEXT, value="40대 부모")
        )

    assert snapshot(state) == before
    assert "customer" not in state.facts


def test_revise_other_field_keeps_pending_llm_question(harness, provider, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    reply(harness, state, AnswerType.DONT_KNOW)
    pending = state.pending_question
    assert (pending.field, pending.level) == ("problem", 1)
    records = list(state.asked_questions)
    calls = len(provider.calls)

    harness.revise_answer(
        state,
        Answer(
            question_id=state.asked_questions[0].question.question_id,
            answer_type=AnswerType.FREE_TEXT,
            value="40대 부모",
        ),
    )

    assert state.pending_question.question_id == pending.question_id
    assert state.asked_questions == records
    assert len(provider.calls) == calls
    assert state.facts["customer"].value == "40대 부모"
    assert state.dont_know_levels == {"problem": 1}


def test_revise_pending_field_clears_ladder_and_advances(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.DONT_KNOW)
    assert state.pending_question.field == "customer"

    harness.revise_answer(
        state,
        Answer(
            question_id=state.asked_questions[0].question.question_id,
            answer_type=AnswerType.FREE_TEXT,
            value="학생",
        ),
    )

    assert state.facts["customer"].value == "학생"
    assert state.dont_know_levels == {}
    assert state.pending_question.field == "problem"


def test_missing_parsed_output_raises_provider_output_error(harness):
    harness.provider = NoParsedProvider()
    with pytest.raises(ProviderOutputError):
        harness.start("향초")


def test_trace_provider_name_is_consistent(harness, provider):
    state = harness.start("향초")
    assert state.trace[0].provider == "mock"
    provider.fail_stages.add("diagnose")
    with pytest.raises(ProviderError):
        harness.diagnose(state)
    failed = state.trace[-1]
    assert failed.provider == "mock"


def test_diagnosis_becomes_assumption_offered_first(harness):
    harness.provider = DiagnosisStub()
    state = harness.start("향초")

    assert state.assumptions["customer"].source is InfoSource.AI_ASSUMPTION
    first = state.pending_question.options[0]
    assert (first.id, first.label, first.ai_suggested) == ("assumed", "30대 직장인", True)


def test_trace_records_concrete_model_on_success_only(harness, provider):
    harness.provider = DiagnosisStub()
    state = harness.start("향초")
    assert (state.trace[0].stage, state.trace[0].provider, state.trace[0].model) == ("diagnose", "mock", "stub")

    harness.provider = provider
    provider.fail_stages.add("diagnose")
    with pytest.raises(ProviderError):
        harness.diagnose(state)
    assert (state.trace[-1].provider, state.trace[-1].model) == ("mock", None)
