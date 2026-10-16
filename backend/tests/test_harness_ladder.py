import pytest

from app.core.state import AnswerType, AskedQuestion, CoachingMode, InfoSource, Question, SessionStatus
from app.harness.base import counted_fields
from app.harness.errors import HarnessError
from app.harness.policy import LadderStep


def test_easier_walks_down_the_ladder_and_stays_on_field(harness, reply):
    state = harness.start("향초")

    reply(harness, state, AnswerType.EASIER)
    q1 = state.pending_question
    assert (q1.field, q1.level) == ("customer", 1)
    assert q1.text == "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?"

    reply(harness, state, AnswerType.EASIER)
    q2 = state.pending_question
    assert (q2.field, q2.level) == ("customer", 2)
    assert [o.label for o in q2.options] == ["나 자신", "다른 사람"]

    reply(harness, state, AnswerType.EASIER)
    q3 = state.pending_question
    assert (q3.field, q3.level, q3.is_ai_proposal) == ("customer", 3, False)
    assert q3.text.startswith("[mock]")
    assert state.trace[-1].stage == "easier_question"
    assert "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?" in state.trace[-1].input["user"]

    reply(harness, state, AnswerType.EASIER)
    q4 = state.pending_question
    assert (q4.field, q4.level, q4.is_ai_proposal) == ("customer", 4, True)
    assert all(o.ai_suggested for o in q4.options)
    assert state.trace[-1].stage == "propose_value"


def test_proposal_repeats_with_previous_candidates_excluded(harness, reply):
    state = harness.start("향초")
    for _ in range(5):
        reply(harness, state, AnswerType.EASIER)

    q5 = state.pending_question
    assert (q5.field, q5.level, q5.is_ai_proposal) == ("customer", 5, True)
    first_candidate = state.asked_questions[-2].question.options[0].label
    assert first_candidate in state.trace[-1].input["user"]


def test_choosing_a_proposal_resolves_field(harness, reply):
    state = harness.start("향초")
    for _ in range(4):
        reply(harness, state, AnswerType.EASIER)
    option_id = state.pending_question.options[0].id

    reply(harness, state, AnswerType.OPTION, option_ids=(option_id,))

    assert state.facts["customer"].source is InfoSource.USER_SELECTED_AI_OPTION
    assert state.easier_levels == {}
    assert state.pending_question.field == "problem"


def test_ladder_retries_do_not_count_toward_cap(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    for _ in range(5):
        reply(harness, state, AnswerType.EASIER)
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")

    assert harness.asked_count(state) == 1
    assert state.pending_question.field == "problem"


def test_skip_leaves_the_ladder(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.EASIER)
    reply(harness, state, AnswerType.SKIP)

    assert state.unknowns == ["customer"]
    assert state.easier_levels == {}
    assert state.pending_question.field == "problem"


# ── 사다리 질문의 다중 선택(#10) ─────────────────────────────


def _walk_to(harness, state, reply, level):
    for _ in range(level):
        reply(harness, state, AnswerType.EASIER)
    assert state.pending_question.level == level
    return state.pending_question


def test_comparison_step_is_single_select_even_for_multi_field(harness, reply):
    harness.policy.field("customer").multi_select = True
    state = harness.start("향초")
    q2 = _walk_to(harness, state, reply, 2)
    assert [o.label for o in q2.options] == ["나 자신", "다른 사람"]
    assert q2.multi_select is False


def test_ladder_step_can_declare_multi_select(harness, reply):
    harness.policy.field("customer").easier_questions[0] = LadderStep(
        question="해당하는 사람을 모두 골라 주세요.", options=["가족", "친구"], multi_select=True
    )
    state = harness.start("향초")
    assert _walk_to(harness, state, reply, 1).multi_select is True


def test_llm_easier_question_follows_field_multi_select(harness, reply):
    harness.policy.field("customer").multi_select = True
    state = harness.start("향초")
    q3 = _walk_to(harness, state, reply, 3)
    assert (q3.is_ai_proposal, q3.multi_select) == (False, True)


def test_ai_proposal_follows_field_multi_select(harness, reply):
    harness.policy.field("customer").multi_select = True
    state = harness.start("향초")
    q4 = _walk_to(harness, state, reply, 4)
    assert (q4.is_ai_proposal, q4.multi_select) == (True, True)


# ── 질문 상한 세기와 '원래 예시 보기' ─────────────────────────


def _record(field: str, level: int, answer_type: AnswerType | None) -> AskedQuestion:
    return AskedQuestion(question=Question(field=field, text="?", level=level), answer_type=answer_type)


def test_counted_fields_are_fields_answered_at_base_level():
    records = [
        _record("a", 0, AnswerType.EASIER),
        _record("a", 1, AnswerType.EASIER),
        _record("a", 0, AnswerType.FREE_TEXT),  # '원래 예시 보기' 뒤 다시 받은 기본 질문
        _record("b", 0, AnswerType.SKIP),
        _record("c", 0, None),  # 걸려 있는 질문은 세지 않는다
    ]
    assert counted_fields(records) == {"a", "b"}


def test_original_returns_to_base_question_without_llm(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.EASIER)
    reply(harness, state, AnswerType.EASIER)
    assert state.pending_question.level == 2
    calls = len(state.trace)

    harness.show_original(state)

    question = state.pending_question
    assert (question.field, question.level, question.is_ai_proposal) == ("customer", 0, False)
    assert question.text == "누구를 위한 건가요?"
    assert [o.label for o in question.options] == ["20대 직장인", "부모", "학생"]
    assert state.easier_levels == {}
    assert state.status is SessionStatus.CLARIFYING
    assert len(state.trace) == calls
    assert state.asked_questions[-1].question.question_id == question.question_id
    assert state.asked_questions[-1].answer_type is None


def test_answer_after_original_counts_the_field_once(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    reply(harness, state, AnswerType.EASIER)
    harness.show_original(state)
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")

    assert harness.asked_count(state) == 1
    assert state.pending_question.field == "problem"


def test_easier_after_original_starts_the_ladder_again(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.EASIER)
    reply(harness, state, AnswerType.EASIER)
    harness.show_original(state)

    reply(harness, state, AnswerType.EASIER)

    assert (state.pending_question.field, state.pending_question.level) == ("customer", 1)


def test_original_needs_a_ladder_question(harness):
    state = harness.start("향초")
    before = state.model_dump(exclude={"trace"})

    with pytest.raises(HarnessError, match="기본 질문으로 돌아갈 사다리 질문이 없습니다."):
        harness.show_original(state)

    assert state.model_dump(exclude={"trace"}) == before
