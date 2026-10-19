"""AI 호출마다 걸린 시간(duration_ms)을 trace에 남긴다. 부르지 않은 기록은 None이다."""
import shutil

import pytest

from app.harness.errors import GenerationFailed
from app.providers.image import MockImageProvider
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness
from tests.test_parallel import PARALLEL_POLICY, PartProvider


def test_successful_calls_record_duration(harness):
    state = harness.start("향초")
    harness.generate(state)
    timed = [t for t in state.trace if t.stage in {"diagnose", "generate"}]
    assert timed and all(isinstance(t.duration_ms, int) and t.duration_ms >= 0 for t in timed)
    summary = [t for t in state.trace if t.output.get("kind") == "summary"]
    assert summary and all(t.duration_ms is None for t in summary)


def test_failed_call_records_duration():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)
    failed = [t for t in state.trace if t.stage == "generate" and "error" in t.output]
    assert isinstance(failed[0].duration_ms, int)


def test_image_call_records_duration(tmp_path):
    target = tmp_path / "sample_task"
    shutil.copytree(SAMPLE_TASK_DIR, target)
    policy = (target / "policy.yaml").read_text(encoding="utf-8") + "\nimage_generation: true\n"
    (target / "policy.yaml").write_text(policy, encoding="utf-8")
    harness = SampleHarness(target, MockProvider(), MockImageProvider())
    state = harness.start("향초")
    harness.generate(state)
    [image] = [t for t in state.trace if t.stage == "image"]
    assert isinstance(image.duration_ms, int)


def test_cached_part_has_no_duration(tmp_path):
    target = tmp_path / "sample_task"
    shutil.copytree(SAMPLE_TASK_DIR, target)
    with (target / "policy.yaml").open("a", encoding="utf-8") as f:
        f.write(PARALLEL_POLICY)
    harness = SampleHarness(target, PartProvider(fail={"plan": 1}))
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)
    harness.generate(state)
    [cached] = [t for t in state.trace if t.output.get("cached")]
    assert cached.duration_ms is None
