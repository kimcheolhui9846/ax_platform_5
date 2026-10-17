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


def test_version_keeps_its_own_copy_of_the_result(harness):
    state = harness.start("향초")
    harness.generate(state)

    state.result.sections[0].heading = "나중에 바뀐 제목"
    state.validation.issues.append(state.validation.issues[0] if state.validation.issues else _issue())

    assert state.versions[0].result.sections[0].heading != "나중에 바뀐 제목"
    assert state.versions[0].validation != state.validation


def test_session_saved_before_versions_gets_version_one_when_read(harness):
    state = harness.start("향초")
    harness.generate(state)
    legacy = state.model_dump(mode="json")
    legacy["versions"] = []  # 버전 기록이 생기기 전에 저장한 세션

    loaded = type(state).model_validate(legacy)

    [version] = loaded.versions
    assert (version.version, version.reason) == (1, VersionReason.FIRST)
    assert version.result == loaded.result
    assert version.facts == loaded.facts


def _issue():
    from app.core.results import ValidationIssue

    return ValidationIssue(rule="r", message="m")
