"""측정 도구: 평가 시나리오를 방식(한 번 호출·병렬)별로 돌려 시간·토큰·경고·비용을 표로 낸다. 테스트는 Mock(비용 0)."""
from pathlib import Path

import pytest

from app.core.state import SessionState, TraceEntry
from app.harness.measure import (
    MEASURE_PARALLEL_PATH,
    call_cost,
    load_parallel_configs,
    measure,
    summarize,
    summary_table,
    write_report,
)
from app.harness.parallel import check_parts
from app.harness.registry import TASK_TYPES, build_harness
from app.providers.base import ProviderResponse, Usage
from app.providers.mock import MockProvider


def test_call_cost_uses_price_table_and_cache_rates():
    usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert call_cost("claude-opus-5-5", usage) == pytest.approx(24.0)
    cached = {"cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}
    assert call_cost("claude-sonnet-5-5", cached) == pytest.approx(2.0 * 0.1 + 2.0 * 1.25)


def test_call_cost_unknown_model_is_none_and_mock_or_failed_call_is_free():
    assert call_cost("other-model", {"input_tokens": 10}) is None
    assert call_cost("mock-image", {}) == call_cost("mock", {"input_tokens": 10}) == 0.0
    assert call_cost(None, {}) == 0.0


def test_summarize_counts_calls_tokens_and_failures():
    state = SessionState(task_type="branding")
    state.trace = [
        TraceEntry(stage="diagnose", model="claude-haiku-5-5", usage={"input_tokens": 100, "output_tokens": 10}, duration_ms=5),
        TraceEntry(stage="generate", output={"error": "잘림"}, duration_ms=7),
        TraceEntry(stage="generate", output={"error": "prompt_leak", "lines": 1}, model="claude-haiku-5-5", duration_ms=3),
        TraceEntry(stage="validate", output={"kind": "summary", "issues": []}),
    ]
    row = summarize(
        "branding", "기본", "single", 1, state, mismatches=["어긋남"], question_ms=12, generate_ms=34, error=""
    )
    assert (row.calls, row.failed_calls, row.prompt_leaks) == (3, 2, 1)
    assert (row.input_tokens, row.output_tokens) == (100, 10)
    assert row.mismatches == 1
    assert row.models == "claude-haiku-5-5"
    assert row.cost_usd == pytest.approx(100 * 0.10 / 1e6 + 10 * 0.50 / 1e6)


def test_parallel_configs_cover_every_task_schema():
    configs = load_parallel_configs(MEASURE_PARALLEL_PATH)
    assert set(configs) == set(TASK_TYPES)
    for task, config in configs.items():
        check_parts(config, build_harness(task, MockProvider()).content_model)


def test_measure_runs_each_scenario_per_variant_and_repeat(tmp_path):
    report = measure(
        tasks=["branding"],
        variants=["single", "parallel"],
        repeat=2,
        provider=MockProvider(),
        parallel_configs=load_parallel_configs(MEASURE_PARALLEL_PATH),
        budget_usd=None,
        workdir=tmp_path,
    )
    scenarios = {row.scenario for row in report.rows}
    assert len(report.rows) == len(scenarios) * 2 * 2
    assert all(row.status == "completed" for row in report.rows)
    assert {row.variant for row in report.rows} == {"single", "parallel"}
    assert not report.stopped_by_budget


class PricedProvider(MockProvider):
    """Mock 응답에 실제 모델 이름과 토큰을 붙여 비용이 쌓이게 한다."""

    def complete(self, **kwargs) -> ProviderResponse:
        response = super().complete(**kwargs)
        return ProviderResponse(
            text=response.text, model="claude-opus-5-5", parsed=response.parsed, usage=Usage(input_tokens=100_000)
        )


def test_measure_stops_when_budget_is_spent(tmp_path):
    report = measure(
        tasks=["branding"],
        variants=["single"],
        repeat=5,
        provider=PricedProvider(),
        parallel_configs={},
        budget_usd=0.01,
        workdir=tmp_path,
    )
    assert len(report.rows) == 1
    assert report.stopped_by_budget


def test_measure_records_errors_without_stopping(tmp_path):
    report = measure(
        tasks=["branding"],
        variants=["single"],
        repeat=1,
        provider=MockProvider(fail_stages={"diagnose"}),
        parallel_configs={},
        budget_usd=None,
        workdir=tmp_path,
    )
    assert report.rows and all(row.status == "error" and "ProviderError" in row.error for row in report.rows)


def test_write_report_saves_rows_and_summary(tmp_path):
    report = measure(
        tasks=["product_planning"],
        variants=["single"],
        repeat=1,
        provider=MockProvider(),
        parallel_configs={},
        budget_usd=None,
        workdir=tmp_path / "work",
    )
    rows_path, summary_path = write_report(report, tmp_path / "out")
    assert rows_path.read_text(encoding="utf-8").splitlines()[0].startswith("task,scenario,variant")
    summary = summary_path.read_text(encoding="utf-8")
    assert "| product_planning | single |" in summary
    assert summary_table(report.rows) in summary


def test_summary_table_shows_percentiles_and_cost():
    from app.harness.measure import RunRow

    rows = [
        RunRow(task="branding", scenario="s", variant="single", repeat=i, status="completed", generate_ms=ms, cost_usd=0.5)
        for i, ms in enumerate([100, 200, 300, 400], start=1)
    ]
    table = summary_table(rows)
    assert "| branding | single | 4 | 4 | 200 | 400 |" in table
    assert "2.0000" in table


def test_script_entry_exists():
    assert (Path(__file__).resolve().parents[2] / "scripts" / "measure.py").exists()
