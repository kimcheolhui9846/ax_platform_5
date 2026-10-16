from app.core.state import AnswerType, CoachingMode, InfoSource


def test_dont_know_walks_down_the_ladder_and_stays_on_field(harness, reply):
    state = harness.start("향초")

    reply(harness, state, AnswerType.DONT_KNOW)
    q1 = state.pending_question
    assert (q1.field, q1.level) == ("customer", 1)
    assert q1.text == "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?"

    reply(harness, state, AnswerType.DONT_KNOW)
    q2 = state.pending_question
    assert (q2.field, q2.level) == ("customer", 2)
    assert [o.label for o in q2.options] == ["나 자신", "다른 사람"]

    reply(harness, state, AnswerType.DONT_KNOW)
    q3 = state.pending_question
    assert (q3.field, q3.level, q3.is_ai_proposal) == ("customer", 3, False)
    assert q3.text.startswith("[mock]")
    assert state.trace[-1].stage == "easier_question"
    assert "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?" in state.trace[-1].input["prompt"]

    reply(harness, state, AnswerType.DONT_KNOW)
    q4 = state.pending_question
    assert (q4.field, q4.level, q4.is_ai_proposal) == ("customer", 4, True)
    assert all(o.ai_suggested for o in q4.options)
    assert state.trace[-1].stage == "propose_value"


def test_proposal_repeats_with_previous_candidates_excluded(harness, reply):
    state = harness.start("향초")
    for _ in range(5):
        reply(harness, state, AnswerType.DONT_KNOW)

    q5 = state.pending_question
    assert (q5.field, q5.level, q5.is_ai_proposal) == ("customer", 5, True)
    first_candidate = state.asked_questions[-2].question.options[0].label
    assert first_candidate in state.trace[-1].input["prompt"]


def test_choosing_a_proposal_resolves_field(harness, reply):
    state = harness.start("향초")
    for _ in range(4):
        reply(harness, state, AnswerType.DONT_KNOW)
    option_id = state.pending_question.options[0].id

    reply(harness, state, AnswerType.OPTION, option_ids=(option_id,))

    assert state.facts["customer"].source is InfoSource.USER_SELECTED_AI_OPTION
    assert state.dont_know_levels == {}
    assert state.pending_question.field == "problem"


def test_ladder_retries_do_not_count_toward_cap(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    for _ in range(5):
        reply(harness, state, AnswerType.DONT_KNOW)
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")

    assert harness.asked_count(state) == 1
    assert state.pending_question.field == "problem"


def test_skip_leaves_the_ladder(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.DONT_KNOW)
    reply(harness, state, AnswerType.SKIP)

    assert state.unknowns == ["customer"]
    assert state.dont_know_levels == {}
    assert state.pending_question.field == "problem"
