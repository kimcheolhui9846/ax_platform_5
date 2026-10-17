"""흐름 패널 목록(plan_flow). 물어본 필드 → 지금 질문 → 앞으로 물을 필드."""
from app.core.state import Answer, AnswerType, CoachingMode
from app.harness.flow import FlowStatus, plan_flow

ANSWERED, CURRENT, UPCOMING, SKIPPED, PAUSED = (
    FlowStatus.ANSWERED,
    FlowStatus.CURRENT,
    FlowStatus.UPCOMING,
    FlowStatus.SKIPPED,
    FlowStatus.PAUSED,
)


def flow_of(harness, state):
    return plan_flow(harness.policy, state, harness.questions_left(state))


def shape(items):
    return [(i.field, i.status) for i in items]


def test_start_shows_current_then_upcoming_within_the_cap(harness):
    state = harness.start("향초")  # 스탠다드 상한 3, idea는 처음 입력, length는 기본값

    items = flow_of(harness, state)

    assert shape(items) == [("customer", CURRENT), ("problem", UPCOMING), ("tone", UPCOMING)]
    current, upcoming = items[0], items[1]
    assert current.question == state.pending_question
    assert (current.label, current.text, current.answer) == ("목표 고객", "누구를 위한 건가요?", None)
    assert (upcoming.text, upcoming.answer, upcoming.question) == ("고객이 겪는 불편은 무엇인가요?", None, None)


def test_quick_mode_shows_fewer_upcoming(harness):
    state = harness.start("향초", mode=CoachingMode.QUICK)  # 상한 2
    assert shape(flow_of(harness, state)) == [("customer", CURRENT), ("problem", UPCOMING)]


def test_answered_field_keeps_its_question_and_value(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))

    items = flow_of(harness, state)

    assert shape(items) == [("customer", ANSWERED), ("problem", CURRENT), ("tone", UPCOMING)]
    assert items[0].answer == "부모"
    assert items[0].question.question_id == state.asked_questions[0].question.question_id


def test_ladder_question_is_current_and_takes_no_extra_slot(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.EASIER)

    items = flow_of(harness, state)

    assert shape(items) == [("customer", CURRENT), ("problem", UPCOMING), ("tone", UPCOMING)]
    assert items[0].text == "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?"
    assert items[0].question.level == 1


def test_skipped_field_is_marked_and_can_be_answered_later(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    reply(harness, state, AnswerType.SKIP)

    items = flow_of(harness, state)
    assert shape(items) == [("customer", ANSWERED), ("problem", SKIPPED), ("tone", CURRENT)]
    skipped = items[1]
    assert skipped.answer is None

    harness.revise_answer(
        state,
        Answer(question_id=skipped.question.question_id, answer_type=AnswerType.FREE_TEXT, value="향이 금방 사라져요"),
    )

    # 미정을 채우자 멈출 때가 돼(준비도 0.9 ≥ 0.8) 걸려 있던 기본 질문(tone)이 내려간다
    items = flow_of(harness, state)
    assert shape(items) == [("customer", ANSWERED), ("problem", ANSWERED)]
    assert items[1].answer == "향이 금방 사라져요"


def test_nothing_upcoming_once_the_harness_stops(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어려워요")

    assert state.pending_question is None
    assert harness.questions_left(state) == 0
    assert shape(flow_of(harness, state)) == [("customer", ANSWERED), ("problem", ANSWERED)]


def test_revised_answer_shows_the_latest_value(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    first = state.asked_questions[0].question.question_id

    harness.revise_answer(state, Answer(question_id=first, answer_type=AnswerType.FREE_TEXT, value="초등학생 부모"))

    item = flow_of(harness, state)[0]
    assert (item.status, item.answer, item.question.question_id) == (ANSWERED, "초등학생 부모", first)


def test_questions_left_counts_down(harness, reply):
    state = harness.start("향초")
    assert harness.questions_left(state) == 3
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")
    assert harness.questions_left(state) == 2


def test_ladder_field_paused_by_an_early_result_stays_counted_and_comes_back(harness, reply):
    state = harness.start("향초")  # 스탠다드 상한 3
    reply(harness, state, AnswerType.EASIER)
    harness.generate(state)  # 사다리 질문을 둔 채 결과를 먼저 만든다(걸린 질문은 내려간다)
    assert state.pending_question is None

    items = flow_of(harness, state)

    # 멈춘 필드는 이미 상한에 셌으므로 '예정' 자리를 쓰지 않는다
    assert shape(items) == [("customer", PAUSED), ("problem", UPCOMING), ("tone", UPCOMING)]
    paused = items[0]
    assert paused.answer is None
    assert paused.question.question_id == state.asked_questions[0].question.question_id

    harness.resume(state)
    assert state.pending_question.field == "customer"  # 이어 가면 다시 묻는다
