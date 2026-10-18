"""다음 과제로 이어가기: 이전 버전의 사실·보완 정보를 새 과제 필드로 가져오고(previous_task), 뺄 수 있다."""
import pytest
import yaml

from app.core.results import GenerationResult, ResultSection, TextBlock, VersionReason
from app.core.state import CarriedContext, CarriedItem, InfoItem, InfoSource, ResultVersion, SessionState
from app.harness.carry import build_context, carry_values, summarize
from app.harness.policy import FieldPolicy, TaskPolicy
from tests.conftest import SAMPLE_TASK_DIR


def info(value: str, source: InfoSource = InfoSource.USER_FREE_TEXT) -> InfoItem:
    return InfoItem(value=value, source=source)


FIELDS = [
    FieldPolicy(name="product", label="홍보 상품", question="q"),
    FieldPolicy(name="target_customer", label="목표 고객", question="q"),
    FieldPolicy(name="tone", label="톤", kind="default", default="중간"),
]


def test_same_name_wins_then_carry_over_in_order_and_facts_before_supplements():
    items = carry_values(
        facts={"product_idea": info("한글 파우치"), "target_customer": info("직장인")},
        supplements={"target_customer": info("학생", InfoSource.USER_SUPPLEMENT), "tone_and_manner": info("담백하게", InfoSource.USER_SUPPLEMENT)},
        fields=FIELDS,
        carry_over={"product_and_customer": "product", "product_idea": "product", "tone_and_manner": "tone"},
        private=frozenset(),
    )
    assert items == [
        CarriedItem(field="product", value="한글 파우치", from_name="product_idea"),
        CarriedItem(field="target_customer", value="직장인", from_name="target_customer"),
        CarriedItem(field="tone", value="담백하게", from_name="tone_and_manner"),
    ]


def test_nothing_to_carry_is_an_empty_list():
    assert carry_values({}, {}, FIELDS, {}, frozenset()) == []


def test_values_that_were_private_in_the_source_stay_marked_private():
    items = carry_values(
        facts={"product_idea": info("비밀 상품")},
        supplements={"target_customer": info("비밀 고객", InfoSource.USER_SUPPLEMENT)},
        fields=FIELDS,
        carry_over={"product_idea": "product"},
        private=frozenset({"product_idea", "target_customer"}),
    )
    assert [(i.field, i.private) for i in items] == [("product", True), ("target_customer", True)]
    assert carry_values({"product": info("a")}, {}, FIELDS, {}, frozenset())[0].private is False


def test_summarize_flattens_spaces_and_clips():
    assert summarize("  한글   파우치\n\n정리  ") == "한글 파우치 정리"
    assert summarize("가" * 200, limit=10) == "가" * 9 + "…"


def source_state() -> tuple[SessionState, ResultVersion]:
    result = GenerationResult(
        sections=[ResultSection(order=1, heading="콘셉트", kind="diagnosis", blocks=[TextBlock(text="작은 물건을 정리하는 한글 파우치")])],
        full_text="",
        content={},
    )
    version = ResultVersion.snapshot(
        2, VersionReason.REGENERATE, result, None,
        {"product_idea": info("한글 파우치")}, {}, [], {"material": info("면", InfoSource.USER_SUPPLEMENT)},
    )
    state = SessionState(session_id="sess_prev", task_type="product_planning", owner_id="owner-0001", result=result, versions=[version])
    return state, version


def test_build_context_names_the_source_version_and_summarizes_the_first_section(harness):
    state, version = source_state()
    harness.policy.carry_over = {"product_idea": harness.policy.raw_input_field}

    context = build_context(state, version, "상품기획", harness.policy, frozenset())

    assert (context.session_id, context.task_type, context.version) == ("sess_prev", "product_planning", 2)
    assert context.title == "상품기획 초안 V2"
    assert context.summary == "작은 물건을 정리하는 한글 파우치"
    assert [i.from_name for i in context.items] == ["product_idea"]


def test_build_context_counts_names_private_in_the_version_or_now_in_the_source(harness):
    state, version = source_state()
    harness.policy.carry_over = {"product_idea": harness.policy.raw_input_field}
    by_version = version.model_copy(update={"private": ["product_idea"]})

    assert build_context(state, by_version, "상품기획", harness.policy, frozenset()).items[0].private is True
    assert build_context(state, version, "상품기획", harness.policy, frozenset({"product_idea"})).items[0].private is True
    assert build_context(state, version, "상품기획", harness.policy, frozenset()).items[0].private is False
    old = version.model_copy(update={"private": None})  # 비공개 기록이 없는 옛 버전
    assert build_context(state, old, "상품기획", harness.policy, frozenset()).items[0].private is False


def test_carried_private_items_are_private_in_the_new_session(harness):
    target = harness.policy.raw_input_field
    context = CarriedContext(
        session_id="sess_prev", task_type="product_planning", version=1, title="t", summary="s",
        items=[CarriedItem(field=target, value="비밀 값", from_name="product_idea", private=True)],
    )
    state = harness.start("새 요청 글", context=context)
    assert target in harness.private(state)


def carried(harness, field: str, value: str) -> CarriedContext:
    return CarriedContext(
        session_id="sess_prev", task_type="product_planning", version=1, title="상품기획 초안 V1", summary="요약",
        items=[CarriedItem(field=field, value=value, from_name=field)],
    )


def test_start_puts_carried_values_in_as_previous_task_facts_and_does_not_ask_them(harness):
    asked_first = harness.start("향초").pending_question.field
    context = carried(harness, asked_first, "이전에서 온 값")

    state = harness.start("향초", context=context)

    assert state.facts[asked_first].value == "이전에서 온 값"
    assert state.facts[asked_first].source is InfoSource.PREVIOUS_TASK
    assert state.context == context
    assert state.pending_question is None or state.pending_question.field != asked_first


def test_carried_value_wins_for_the_raw_input_field_and_clearing_restores_the_request_text(harness):
    target = harness.policy.raw_input_field
    state = harness.start("새 요청 글", context=carried(harness, target, "이전 글"))
    assert (state.facts[target].value, state.facts[target].source) == ("이전 글", InfoSource.PREVIOUS_TASK)
    assert state.raw_input == "새 요청 글"  # 새 요청 글은 처음 입력으로 프롬프트에 남는다

    harness.clear_context(state)

    assert (state.facts[target].value, state.facts[target].source) == ("새 요청 글", InfoSource.USER_FREE_TEXT)


def test_default_facts_of_the_previous_session_are_not_carried():
    items = carry_values(
        facts={"tone": info("중간", InfoSource.DEFAULT)},
        supplements={},
        fields=FIELDS,
        carry_over={},
        private=frozenset(),
    )
    assert items == []


def test_clear_context_with_nothing_left_to_remove_only_drops_the_context(harness):
    first = harness.start("향초").pending_question.field
    other = next(f.name for f in harness.policy.fields if f.kind != "default" and f.name not in (first, harness.policy.raw_input_field))
    state = harness.start("향초", context=carried(harness, other, "가져온 값"))
    state.facts[other] = info("사용자가 고친 값")
    state.pending_question = None  # 걸린 질문이 없어도 다시 묻지 않는다
    before = state.model_copy(deep=True)

    harness.clear_context(state)

    assert state.context is None
    assert state.model_copy(update={"context": before.context}) == before


def test_clear_context_removes_only_values_still_from_the_previous_task(harness):
    first = harness.start("향초").pending_question.field
    other = next(f.name for f in harness.policy.fields if f.kind != "default" and f.name not in (first, harness.policy.raw_input_field))
    context = CarriedContext(
        session_id="sess_prev", task_type="product_planning", version=1, title="t", summary="s",
        items=[CarriedItem(field=first, value="가져온 값", from_name=first), CarriedItem(field=other, value="가져온 값2", from_name=other)],
    )
    state = harness.start("향초", context=context)
    state.facts[other] = info("사용자가 고친 값")  # 가져온 뒤 사용자가 바꾼 값은 남는다

    harness.clear_context(state)

    assert first not in state.facts
    assert state.facts[other].value == "사용자가 고친 값"
    assert state.context is None


def test_clear_context_after_a_result_recomputes_staleness(harness):
    first = harness.start("향초").pending_question.field
    state = harness.start("향초", context=carried(harness, first, "가져온 값"))
    harness.generate(state)
    assert state.result_stale is False

    harness.clear_context(state)

    assert state.result_stale is True
    assert state.status.value == "clarifying"  # 빠진 항목을 다시 묻는다


def test_clear_context_without_context_changes_nothing(harness):
    state = harness.start("향초")
    before = state.model_copy(deep=True)
    harness.clear_context(state)
    assert state == before


def test_generate_prompt_shows_the_previous_result(harness):
    first = harness.start("향초").pending_question.field
    state = harness.start("향초", context=carried(harness, first, "가져온 값"))
    harness.generate(state)
    prompt = next(t for t in state.trace if t.stage == "generate").input
    assert "## 이전 과제 결과" in prompt["user"] and "상품기획 초안 V1" in prompt["user"]
    assert "상품기획 초안 V1" not in prompt["system"]


def test_carry_over_targets_must_be_fields():
    data = yaml.safe_load((SAMPLE_TASK_DIR / "policy.yaml").read_text(encoding="utf-8"))
    data["carry_over"] = {"anything": "not_a_field"}
    with pytest.raises(ValueError, match="carry_over"):
        TaskPolicy.model_validate(data)


def test_clear_context_restores_the_policy_default_of_a_default_field(harness):
    state = harness.start("향초", context=carried(harness, "length", "길게"))
    assert state.facts["length"].source is InfoSource.PREVIOUS_TASK

    harness.clear_context(state)

    assert state.facts["length"].value == "중간"
    assert state.facts["length"].source is InfoSource.DEFAULT


def test_clear_context_asks_a_removed_field_again_when_no_question_is_pending(harness):
    first = harness.start("향초").pending_question.field
    context = carried(harness, first, "가져온 값")
    state = harness.start("향초", context=context)
    state.pending_question = None  # 질문이 모두 끝난 세션
    state.asked_questions = []

    harness.clear_context(state)

    assert state.pending_question is not None and state.pending_question.field == first
    assert state.status.value == "clarifying"


def test_clear_context_leaves_a_pending_question_on_another_field_alone(harness):
    first = harness.start("향초").pending_question.field
    other = next(f.name for f in harness.policy.fields if f.kind != "default" and f.name not in (first, harness.policy.raw_input_field))
    context = CarriedContext(
        session_id="sess_prev", task_type="product_planning", version=1, title="t", summary="s",
        items=[CarriedItem(field=other, value="가져온 값", from_name=other)],
    )
    state = harness.start("향초", context=context)
    pending = state.pending_question
    assert pending is not None and pending.field != other

    harness.clear_context(state)

    assert state.pending_question.question_id == pending.question_id


def test_clear_context_keeps_privacy_of_carried_values_the_user_changed(harness):
    first = harness.start("향초").pending_question.field
    others = [f.name for f in harness.policy.fields if f.kind != "default" and f.name not in (first, harness.policy.raw_input_field)]
    kept, dropped = others[0], others[1]
    context = CarriedContext(
        session_id="sess_prev", task_type="product_planning", version=1, title="t", summary="s",
        items=[
            CarriedItem(field=kept, value="가져온 값", from_name=kept, private=True),
            CarriedItem(field=dropped, value="가져온 값", from_name=dropped, private=True),
        ],
    )
    state = harness.start("향초", context=context)
    state.facts[kept] = info("사용자가 고친 값")

    harness.clear_context(state)

    assert kept in harness.private(state)
    assert dropped not in harness.private(state)
