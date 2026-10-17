"""결과 버전: 생성할 때마다 하나씩 쌓이고, 그때의 기준(사실·가정·미정)을 함께 남긴다."""
import pytest

from app.core.results import VersionReason
from app.core.state import AnswerType
from app.harness.base import find_version
from app.harness.errors import GenerationFailed


def test_first_generate_records_version_one_with_its_basis(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    reply(harness, state, AnswerType.SKIP)

    harness.generate(state)

    [version] = state.versions
    assert (version.version, version.reason, version.saved) == (1, VersionReason.FIRST, False)
    assert version.result == state.result
    assert version.validation == state.validation
    assert version.created_at == state.result.generated_at
    assert version.facts["customer"].value == "부모"
    assert version.unknowns == ["problem"]


def test_regenerate_adds_a_version_and_keeps_the_earlier_basis(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    first_question = state.asked_questions[0].question.question_id
    harness.revise_answer(state, _free_text(first_question, "초등학생 부모"))

    harness.generate(state)

    assert [(v.version, v.reason) for v in state.versions] == [(1, VersionReason.FIRST), (2, VersionReason.REGENERATE)]
    assert state.versions[0].facts["customer"].value == "부모"
    assert state.versions[1].facts["customer"].value == "초등학생 부모"
    assert state.versions[-1].result == state.result


def test_failed_generate_adds_no_version(harness, provider, reply):
    state = harness.start("향초")
    harness.generate(state)
    provider.fail_stages.add("generate")

    with pytest.raises(GenerationFailed):
        harness.generate(state)

    assert [v.version for v in state.versions] == [1]


def test_save_marks_one_version_and_ignores_unknown_numbers(harness):
    state = harness.start("향초")
    harness.generate(state)
    harness.generate(state)

    saved = harness.save_version(state, 1)

    assert saved is state.versions[0]
    assert [v.saved for v in state.versions] == [True, False]
    assert harness.save_version(state, 1) is state.versions[0]  # 다시 저장해도 그대로다
    assert harness.save_version(state, 3) is None
    assert harness.save_version(state, 0) is None


def test_find_version():
    assert find_version([], 1) is None


def _free_text(question_id: str, value: str):
    from app.core.state import Answer

    return Answer(question_id=question_id, answer_type=AnswerType.FREE_TEXT, value=value)
