import pytest

from app.core.results import GenerationResult
from app.core.state import (
    Answer,
    AnswerType,
    Assumption,
    CoachingMode,
    InfoSource,
    Question,
    QuestionOption,
    SessionStatus,
)
from app.harness.errors import HarnessError


def test_start_sets_raw_input_fact_defaults_and_first_question(harness):
    state = harness.start("향초 만들기")

    assert state.facts["idea"].value == "향초 만들기"
    assert state.facts["idea"].source is InfoSource.USER_FREE_TEXT
    assert state.facts["length"].source is InfoSource.DEFAULT
    assert state.status is SessionStatus.CLARIFYING
    assert state.pending_question.field == "customer"
    assert [o.label for o in state.pending_question.options] == ["20대 직장인", "부모", "학생"]
    assert state.readiness == 0.4
    assert state.trace[0].stage == "diagnose"
    assert len(state.asked_questions) == 1


def test_option_answer_becomes_fact_and_moves_on(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))

    assert state.facts["customer"].value == "부모"
    assert state.facts["customer"].source is InfoSource.USER_SELECTED_AI_OPTION
    assert state.pending_question.field == "problem"
    assert state.asked_questions[0].value == "부모"


def test_free_text_answer_is_stripped(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.FREE_TEXT, value="  집들이 가는 30대  ")
    assert state.facts["customer"].value == "집들이 가는 30대"
    assert state.facts["customer"].source is InfoSource.USER_FREE_TEXT


def test_invalid_answers_rejected(harness, reply):
    state = harness.start("향초")
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.FREE_TEXT, value="   ")
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION, option_ids=("o9",))
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION, option_ids=("o1", "o2"))
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION)
    with pytest.raises(HarnessError):
        harness.apply_answer(state, Answer(question_id="q_다른질문", answer_type=AnswerType.SKIP))
    assert "customer" not in state.facts
    assert state.asked_questions[-1].answer_type is None


def test_stops_when_must_fields_filled_and_ready(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")

    assert state.readiness == 0.9
    assert state.pending_question is None
    assert state.status is SessionStatus.CONFIRMING


def test_stops_at_mode_question_cap(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    reply(harness, state, AnswerType.SKIP)
    reply(harness, state, AnswerType.SKIP)

    assert state.unknowns == ["customer", "problem"]
    assert harness.asked_count(state) == 2
    assert state.pending_question is None
    assert state.status is SessionStatus.CONFIRMING


def test_multi_select_joins_labels(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.SKIP)
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")
    assert state.pending_question.field == "tone"
    assert state.pending_question.multi_select

    reply(harness, state, AnswerType.OPTION, option_ids=("o1", "o3"))
    assert state.facts["tone"].value == "따뜻한, 유쾌한"


def test_assumption_offered_as_first_option(harness, reply):
    state = harness.start("향초")
    state.assumptions["customer"] = Assumption(
        value="30대 직장인", source=InfoSource.AI_ASSUMPTION, confidence=0.5
    )
    harness.advance(state)

    first = state.pending_question.options[0]
    assert (first.id, first.label, first.ai_suggested) == ("assumed", "30대 직장인", True)
    assert state.readiness == 0.55
    assert len(state.asked_questions) == 1

    reply(harness, state, AnswerType.OPTION, option_ids=("assumed",))
    assert state.facts["customer"].value == "30대 직장인"
    assert "customer" not in state.assumptions


def test_revise_answer_updates_fact(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    question_id = state.asked_questions[0].question.question_id

    harness.revise_answer(
        state, Answer(question_id=question_id, answer_type=AnswerType.FREE_TEXT, value="40대 부모")
    )

    assert state.facts["customer"].value == "40대 부모"
    assert state.asked_questions[0].value == "40대 부모"
    assert state.pending_question.field == "problem"


def test_revise_rejects_unknown_unanswered_and_non_value_answers(harness, reply):
    state = harness.start("향초")
    with pytest.raises(HarnessError):
        harness.revise_answer(state, Answer(question_id="q_없음", answer_type=AnswerType.FREE_TEXT, value="x"))
    with pytest.raises(HarnessError):
        harness.revise_answer(
            state,
            Answer(question_id=state.pending_question.question_id, answer_type=AnswerType.FREE_TEXT, value="x"),
        )
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    with pytest.raises(HarnessError):
        harness.revise_answer(
            state,
            Answer(question_id=state.asked_questions[0].question.question_id, answer_type=AnswerType.DONT_KNOW),
        )


def test_revise_after_result_marks_stale(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")
    state.result = GenerationResult(cards=[], full_text="이전 결과", content={})

    harness.revise_answer(
        state,
        Answer(
            question_id=state.asked_questions[0].question.question_id,
            answer_type=AnswerType.FREE_TEXT,
            value="40대 부모",
        ),
    )

    assert state.result_stale
    assert state.status is SessionStatus.REVISING


def test_unknown_option_message_lists_ids_without_python_repr():
    from app.harness.base import answer_to_fact

    question = Question(field="f", text="q", options=[QuestionOption(id="o1", label="a")], multi_select=True)
    answer = Answer(question_id=question.question_id, answer_type=AnswerType.OPTION, option_ids=["o9", "o8"])
    with pytest.raises(HarnessError) as caught:
        answer_to_fact(question, answer)
    assert str(caught.value) == "없는 선택지입니다: o9, o8"
