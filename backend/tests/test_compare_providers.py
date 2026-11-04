"""제공자 비교(TC3): 같은 평가 시나리오를 제공자마다 돌려 나란히 표로 낸다. 테스트는 Mock(비용 0)."""
import os
import subprocess
import sys
from pathlib import Path

from app.harness.measure import compare, provider_totals, write_comparison
from app.providers.base import ProviderResponse, Usage
from app.providers.mock import MockProvider

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "compare_providers.py"
BACKEND = Path(__file__).resolve().parents[1]


class PricedProvider(MockProvider):
    """Mock 응답에 실제 모델 이름과 토큰을 붙여 비용이 쌓이게 한다(호출마다 $0.4)."""

    def complete(self, **kwargs) -> ProviderResponse:
        response = super().complete(**kwargs)
        return ProviderResponse(
            text=response.text, model="claude-opus-5-5", parsed=response.parsed, usage=Usage(input_tokens=100_000)
        )


def test_compare_runs_same_scenarios_for_every_provider(tmp_path):
    reports = compare(
        providers={"first": MockProvider(), "second": MockProvider()},
        tasks=["branding", "ir_pitch"],
        repeat=1,
        budget_usd=None,
        workdir=tmp_path,
    )
    assert list(reports) == ["first", "second"]
    runs = [{(r.task, r.scenario, r.variant) for r in report.rows} for report in reports.values()]
    assert runs[0] == runs[1]
    assert {variant for _, _, variant in runs[0]} == {"single"}
    assert all(r.status == "completed" for report in reports.values() for r in report.rows)


def test_compare_splits_budget_equally_between_providers(tmp_path):
    reports = compare(
        providers={"first": PricedProvider(), "second": PricedProvider()},
        tasks=["branding"],
        repeat=3,
        budget_usd=0.02,
        workdir=tmp_path,
    )
    for report in reports.values():
        assert len(report.rows) == 1
        assert report.stopped_by_budget


def test_write_comparison_saves_totals_and_each_provider_report(tmp_path):
    reports = compare(
        providers={"first": MockProvider(), "second": MockProvider()},
        tasks=["product_planning"],
        repeat=1,
        budget_usd=None,
        workdir=tmp_path / "work",
    )
    path = write_comparison(reports, tmp_path / "out")
    text = path.read_text(encoding="utf-8")
    assert path == tmp_path / "out" / "compare.md"
    assert provider_totals({name: report.rows for name, report in reports.items()}) in text
    assert "## first" in text and "## second" in text
    for name in reports:
        assert (tmp_path / "out" / name / "rows.csv").exists()
        assert list((tmp_path / "out" / name / "documents").glob("*.md"))


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PROVIDER": "mock"},
        timeout=120,
    )


def test_compare_script_with_mock_writes_comparison(tmp_path):
    done = _run_script("--providers", "mock", "--tasks", "branding", "--out", str(tmp_path))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "| mock |" in (tmp_path / "compare.md").read_text(encoding="utf-8")


def test_compare_script_refuses_real_provider_without_budget(tmp_path):
    done = _run_script("--providers", "claude", "openai", "--out", str(tmp_path))
    assert done.returncode == 2
    assert not (tmp_path / "compare.md").exists()


def test_compare_script_refuses_same_provider_twice(tmp_path):
    done = _run_script("--providers", "mock", "mock", "--out", str(tmp_path))
    assert done.returncode == 2


def test_compare_needs_at_least_one_provider(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        compare(providers={}, tasks=["branding"], repeat=1, budget_usd=1.0, workdir=tmp_path)
