"""병렬 생성(기본 꺼짐): 결과 항목을 조각으로 나눠 동시에 부르고 코드로 합친다. 끝난 조각은 캐시에 남는다."""
import shutil
import threading

import pytest
from pydantic import ValidationError

from app.core.results import CardType, ResultAssumption, ResultCard
from app.core.state import SessionStatus
from app.harness.errors import GenerationFailed
from app.harness.parallel import check_parts, merge_parts, part_models
from app.harness.policy import GenerationPart, ParallelGeneration
from app.providers.base import ProviderBusy, ProviderError
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleContent, SampleHarness

PARALLEL_POLICY = """
parallel_generation:
  max_workers: 2
  parts:
    - name: overview
      content: [summary]
    - name: plan
      content: [actions]
"""


def part_of(response_model) -> str:
    """조각 응답 모델이 다루는 content 필드로 조각을 가린다."""
    fields = set(response_model.model_fields["content"].annotation.model_fields)
    return "overview" if fields == {"summary"} else "plan"


class PartProvider(MockProvider):
    """조각별로 실패를 지정할 수 있는 Mock. fail은 조각 이름 → 남은 실패 횟수, errors는 그때 던질 예외."""

    def __init__(self, fail=None, error=ProviderError, barrier=None):
        super().__init__()
        self.fail = dict(fail or {})
        self.error = error
        self.barrier = barrier
        self.parts: list[str] = []

    def complete(self, *, task_type, stage, prompt, response_model=None):
        if stage == "generate_part":
            part = part_of(response_model)
            self.parts.append(part)
            if self.barrier is not None:
                self.barrier.wait()  # 두 조각이 동시에 돌지 않으면 시간 초과로 깨진다
            if self.fail.get(part, 0) > 0:
                self.fail[part] -= 1
                raise self.error(f"[test] {part} 실패")
        return super().complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)


@pytest.fixture
def task_dir(tmp_path):
    target = tmp_path / "sample_task"
    shutil.copytree(SAMPLE_TASK_DIR, target)
    with (target / "policy.yaml").open("a", encoding="utf-8") as f:
        f.write(PARALLEL_POLICY)
    return target


# ── 정책 ────────────────────────────────────────────────


def test_parallel_generation_is_off_by_default(harness):
    assert harness.policy.parallel_generation is None


def test_policy_rejects_overlapping_parts():
    with pytest.raises(ValidationError, match="summary"):
        ParallelGeneration(
            parts=[GenerationPart(name="a", content=["summary"]), GenerationPart(name="b", content=["summary", "actions"])]
        )


def test_policy_rejects_duplicate_part_names():
    with pytest.raises(ValidationError, match="a"):
        ParallelGeneration(parts=[GenerationPart(name="a", content=["summary"]), GenerationPart(name="a", content=["actions"])])


def test_policy_needs_two_parts():
    with pytest.raises(ValidationError):
        ParallelGeneration(parts=[GenerationPart(name="a", content=["summary", "actions"])])


def test_parts_must_cover_content_model_exactly():
    covering = ParallelGeneration(
        parts=[GenerationPart(name="a", content=["summary"]), GenerationPart(name="b", content=["actions"])]
    )
    check_parts(covering, SampleContent)
    missing = ParallelGeneration(
        parts=[GenerationPart(name="a", content=["summary"]), GenerationPart(name="b", content=["없는필드"])]
    )
    with pytest.raises(ValueError, match="actions"):
        check_parts(missing, SampleContent)


def test_harness_rejects_parts_that_do_not_match_schema(task_dir):
    policy = (task_dir / "policy.yaml").read_text(encoding="utf-8").replace("[actions]", "[없는필드]")
    (task_dir / "policy.yaml").write_text(policy, encoding="utf-8")
    with pytest.raises(ValueError, match="없는필드"):
        SampleHarness(task_dir, MockProvider())


def test_part_models_hold_only_their_fields():
    parallel = ParallelGeneration(
        parts=[GenerationPart(name="a", content=["summary"]), GenerationPart(name="b", content=["actions"])]
    )
    models = part_models(parallel, SampleContent)
    assert set(models) == {"a", "b"}
    assert set(models["a"].model_fields["content"].annotation.model_fields) == {"summary"}
    assert "full_text" not in models["a"].model_fields


# ── 합치기 ──────────────────────────────────────────────


def card(title: str, order: int) -> ResultCard:
    return ResultCard(card_type=CardType.SUGGESTION, title=title, body=f"{title} 본문", order=order)


SPLIT = ParallelGeneration(
    parts=[GenerationPart(name="overview", content=["summary"]), GenerationPart(name="plan", content=["actions"])]
)


def test_merge_parts_joins_content_cards_and_assumptions():
    models = part_models(SPLIT, SampleContent)
    overview = models["overview"](
        cards=[card("요약 2", 2), card("요약 1", 1)],
        assumptions=[ResultAssumption(field="customer", value="20대")],
        content={"summary": "요약"},
    )
    plan = models["plan"](
        cards=[card("실행", 1)],
        assumptions=[ResultAssumption(field="customer", value="다른 값"), ResultAssumption(field="problem", value="불편")],
        content={"actions": ["하나"]},
    )
    result = merge_parts([overview, plan], SampleContent)

    assert result.content == {"summary": "요약", "actions": ["하나"]}
    assert [(s.order, s.heading) for s in result.sections] == [(1, "요약 1"), (2, "요약 2"), (3, "실행")]
    assert [(a.field, a.value) for a in result.assumptions] == [("customer", "20대"), ("problem", "불편")]
    assert result.full_text == "요약 1\n요약 1 본문\n\n요약 2\n요약 2 본문\n\n실행\n실행 본문"


def test_merge_parts_validates_whole_content():
    with pytest.raises(ValidationError):
        merge_parts([part_models(SPLIT, SampleContent)["overview"](cards=[], content={"summary": "요약"})], SampleContent)


# ── 하네스 ──────────────────────────────────────────────


def test_parallel_generate_calls_each_part_once(task_dir):
    provider = PartProvider()
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert sorted(provider.parts) == ["overview", "plan"]
    assert not any(stage == "generate" for _, stage in provider.calls)
    SampleContent.model_validate(state.result.content)
    assert [t.stage for t in state.trace if t.stage == "generate_part"] == ["generate_part", "generate_part"]
    assert state.generation_parts == {}
    assert len(state.versions) == 1


def test_parts_run_concurrently(task_dir):
    provider = PartProvider(barrier=threading.Barrier(2, timeout=5))
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")
    harness.generate(state)
    assert state.status is SessionStatus.COMPLETED


def test_failed_part_keeps_finished_parts_and_retries_only_failed(task_dir):
    provider = PartProvider(fail={"plan": 1})
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")

    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED
    assert set(state.generation_parts) == {"overview"}
    assert state.versions == []

    provider.parts.clear()
    harness.generate(state)
    assert provider.parts == ["plan"]
    assert state.status is SessionStatus.COMPLETED
    assert state.generation_parts == {}


def test_changed_input_does_not_reuse_cached_part(task_dir, reply):
    provider = PartProvider(fail={"plan": 1})
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)

    from app.core.state import AnswerType

    reply(harness, state, AnswerType.FREE_TEXT, "새로운 답")
    provider.parts.clear()
    harness.generate(state)
    assert sorted(provider.parts) == ["overview", "plan"]


def test_busy_part_rolls_back_without_failing_and_keeps_cache(task_dir):
    provider = PartProvider(fail={"plan": 1}, error=ProviderBusy)
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")
    before = state.status

    with pytest.raises(ProviderBusy):
        harness.generate(state)
    assert state.status is before
    assert set(state.generation_parts) == {"overview"}


def test_schema_error_retries_only_that_part(task_dir):
    from app.providers.base import ProviderOutputError

    provider = PartProvider(fail={"overview": 1}, error=ProviderOutputError)
    harness = SampleHarness(task_dir, provider)
    state = harness.start("향초")
    harness.generate(state)
    assert sorted(provider.parts) == ["overview", "overview", "plan"]
    assert state.status is SessionStatus.COMPLETED
