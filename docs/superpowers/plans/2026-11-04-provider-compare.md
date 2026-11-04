# TC3 OpenAI vs Claude 비교 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 같은 평가 시나리오를 Claude와 OpenAI(GPT)로 돌려 시간·토큰·비용·결과 품질을 나란히 비교하는 도구를 만들고(비용 0 Mock으로 자동 테스트), 사용자 승인 뒤 실제로 한 번 돌려 결과를 문서로 남긴다(TC3).

**Architecture:** 측정 도구(`backend/app/harness/measure.py`)는 이미 제공자 하나로 과제 × 시나리오를 돈다. 여기에 (1) 실행마다 결과 글(`full_text`)을 남기는 `RunDocument`(품질을 눈으로 비교), (2) 제공자별 합계 표 `provider_totals`(순수), (3) 여러 제공자를 같은 시나리오로 돌리는 `compare`·`write_comparison`을 더하고, 진입점 `scripts/compare_providers.py`를 둔다. 과제별 표의 칸 계산은 기존 `summary_table`과 합계 표가 같은 도우미(`_group_cells`)를 쓴다.

**Tech Stack:** Python 3, Pydantic v2, pytest, 기존 `MockProvider`·`ClaudeProvider`·`OpenAIProvider`.

## Global Constraints

- 실제 모델 호출은 비용이 든다. **예산 상한 $5**, 실행 직전 사용자 승인. 자동 테스트는 모두 Mock(비용 0).
- 비교 방식은 한 번 호출(`single`)만 돈다(병렬 생성은 모든 과제에서 꺼져 있다).
- 예산(`--budget-usd`)은 제공자마다 똑같이 나눈다. 실제 제공자가 하나라도 있으면 `--budget-usd`가 없을 때 종료 코드 2로 멈춘다(키·제공자를 만들기 전에).
- `backend/.env`는 읽거나 고치지 않는다. 키를 출력하지 않는다. 결과 폴더(`backend/data/`)는 git에서 제외돼 있다.
- 코드 품질: 판단은 순수 함수, 제어 결합(동작을 바꾸는 플래그 인자) 금지, 필요한 데이터만 넘긴다.
- 커밋 메시지에 AI 공동저자·생성 표기 금지. 줄바꿈 LF.
- 명령: `uv run --directory backend pytest`.

---

### Task 1: 결과 글·제공자 합계·비교 도구

**Files:**
- Modify: `backend/app/harness/measure.py`
- Create: `scripts/compare_providers.py`
- Test: `backend/tests/test_measure.py` (추가), `backend/tests/test_compare_providers.py` (신규)

**Interfaces:**
- Produces (Task 2가 문서에서 가리킨다):
  - `RunDocument(task, scenario, variant, repeat, full_text)`; `MeasureReport.documents: list[RunDocument]`
  - `run_once(...) -> tuple[RunRow, RunDocument | None]`
  - `provider_totals(results: Mapping[str, Sequence[RunRow]]) -> str`
  - `compare(*, providers: Mapping[str, LLMProvider], tasks: Sequence[str], repeat: int, budget_usd: float | None, workdir: Path) -> dict[str, MeasureReport]`
  - `write_comparison(reports: Mapping[str, MeasureReport], out_dir: Path) -> Path` (`out_dir/compare.md`, 제공자마다 `out_dir/<이름>/rows.csv·summary.md·documents/*.md`)
  - 테스트 이름(Task 2의 YAML이 가리킨다): `tests/test_compare_providers.py::test_compare_runs_same_scenarios_for_every_provider`, `tests/test_compare_providers.py::test_compare_script_with_mock_writes_comparison`

- [ ] **Step 1: 실패하는 테스트 — 결과 글**

`backend/tests/test_measure.py` 끝에 더한다:

```python
def test_measure_keeps_result_text_of_each_generated_run(tmp_path):
    report = measure(
        tasks=["product_planning"],
        variants=["single"],
        repeat=1,
        provider=MockProvider(),
        parallel_configs={},
        budget_usd=None,
        workdir=tmp_path,
    )
    assert len(report.documents) == len(report.rows)
    assert {(d.task, d.scenario) for d in report.documents} == {(r.task, r.scenario) for r in report.rows}
    assert all(d.full_text for d in report.documents)


def test_measure_has_no_document_when_generation_fails(tmp_path):
    report = measure(
        tasks=["product_planning"],
        variants=["single"],
        repeat=1,
        provider=MockProvider(fail_stages={"generate"}),
        parallel_configs={},
        budget_usd=None,
        workdir=tmp_path,
    )
    assert report.rows and all(row.status == "failed" for row in report.rows)
    assert report.documents == []


def test_write_report_saves_each_result_text(tmp_path):
    report = measure(
        tasks=["product_planning"],
        variants=["single"],
        repeat=1,
        provider=MockProvider(),
        parallel_configs={},
        budget_usd=None,
        workdir=tmp_path / "work",
    )
    write_report(report, tmp_path / "out")
    saved = sorted((tmp_path / "out" / "documents").glob("*.md"))
    assert len(saved) == len(report.documents)
    assert {p.read_text(encoding="utf-8") for p in saved} == {d.full_text for d in report.documents}


def test_document_name_is_safe_file_name():
    from app.harness.measure import RunDocument, document_name

    doc = RunDocument(task="branding", scenario='a/b:c*"?', variant="single", repeat=2, full_text="x")
    assert document_name(doc) == "branding-single-2-a_b_c___.md"
```

- [ ] **Step 2: 실패하는 테스트 — 제공자 합계 표**

`backend/tests/test_measure.py` 끝에 더한다:

```python
def test_provider_totals_shows_one_row_per_provider_with_models_and_cost():
    from app.harness.measure import RunRow, provider_totals

    def row(task: str, status: str, ms: int, models: str, cost: float) -> RunRow:
        return RunRow(task=task, scenario="s", variant="single", repeat=1, status=status, generate_ms=ms, models=models, cost_usd=cost)

    table = provider_totals({
        "claude": [row("branding", "completed", 100, "claude-sonnet-5-5", 0.1), row("ir_pitch", "completed", 300, "claude-sonnet-5-5", 0.2)],
        "openai": [row("branding", "completed", 200, "gpt-6.1-terra", 0.05), row("ir_pitch", "failed", 0, "gpt-6.1-terra", 0.01)],
    })
    lines = table.splitlines()
    assert lines[0].startswith("| 제공자 | 모델 | 실행 | 완료 |")
    assert "| claude | claude-sonnet-5-5 | 2 | 2 | 100 | 300 |" in table
    assert "| openai | gpt-6.1-terra | 2 | 1 | 200 | 200 |" in table
    assert "0.3000" in table and "0.0600" in table


def test_summary_table_columns_match_provider_totals():
    from app.harness.measure import RunRow, provider_totals

    rows = [RunRow(task="branding", scenario="s", variant="single", repeat=1, status="completed", generate_ms=10)]
    summary_cells = summary_table(rows).splitlines()[2].split("|")[3:]
    totals_cells = provider_totals({"mock": rows}).splitlines()[2].split("|")[3:]
    assert summary_cells == totals_cells
```

- [ ] **Step 3: 실패하는 테스트 — 비교**

`backend/tests/test_compare_providers.py`:

```python
"""제공자 비교(TC3): 같은 평가 시나리오를 제공자마다 돌려 나란히 표로 낸다. 테스트는 Mock(비용 0)."""
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
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PROVIDER": "mock"},
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
```

- [ ] **Step 4: 실패 확인**

Run: `uv run --directory backend pytest tests/test_measure.py tests/test_compare_providers.py -q`
Expected: FAIL (`documents`, `document_name`, `provider_totals`, `compare`, `write_comparison`, 스크립트 없음)

- [ ] **Step 5: `measure.py` 구현**

`import re`를 import 묶음에 더한다(`import math` 다음). `LLMProvider` import는 이미 있다.

`MeasureReport` 위에 더하고 `MeasureReport`를 바꾼다:

```python
class RunDocument(BaseModel):
    """실행 한 번이 만든 결과 글(품질을 눈으로 비교). 생성까지 가지 못한 실행은 남지 않는다."""

    task: str
    scenario: str
    variant: str
    repeat: int
    full_text: str


class MeasureReport(BaseModel):
    rows: list[RunRow]
    documents: list[RunDocument] = []
    stopped_by_budget: bool = False
```

`run_once`를 바꾼다(반환 형식과 끝부분만):

```python
def run_once(
    harness: BaseHarness, scenario_name: str, scenario, variant: str, repeat: int
) -> tuple[RunRow, RunDocument | None]:
    """시나리오 한 번. 질문 단계와 생성의 벽시계 시간을 따로 잰다. 예외는 기록하고 다음 실행으로 넘어간다."""
    # ... 기존 본문 그대로 ...
    row = summarize(
        harness.task_type, scenario_name, variant, repeat, state,
        mismatches=mismatches, question_ms=question_ms, generate_ms=generate_ms, error=error,
    )
    result = state.result if state is not None else None
    document = (
        RunDocument(task=harness.task_type, scenario=scenario_name, variant=variant, repeat=repeat, full_text=result.full_text)
        if result is not None
        else None
    )
    return row, document
```

`measure` 본문을 바꾼다:

```python
    rows: list[RunRow] = []
    documents: list[RunDocument] = []
    spent = 0.0
    for task in tasks:
        for variant in variants:
            harness = variant_harness(task, variant, provider, parallel_configs, workdir)
            for scenario in load_scenarios(harness.task_dir):
                for n in range(1, repeat + 1):
                    if budget_usd is not None and spent >= budget_usd:
                        return MeasureReport(rows=rows, documents=documents, stopped_by_budget=True)
                    row, document = run_once(harness, scenario.name, scenario, variant, n)
                    rows.append(row)
                    if document is not None:
                        documents.append(document)
                    spent += row.cost_usd or 0.0
    return MeasureReport(rows=rows, documents=documents)
```

`summary_table`의 칸 계산을 도우미로 빼고 합계 표를 더한다(기존 `SUMMARY_HEADER`·`summary_table` 자리를 아래로 바꾼다):

```python
STAT_COLUMNS = (
    "실행 | 완료 | 생성 p50(ms) | 생성 p95(ms) | 질문 평균(ms) | 호출 평균 | 실패 호출 | 유출 차단 "
    "| 입력 토큰 평균 | 출력 토큰 평균 | 경고 평균 | 계획 어긋남 | 비용 합($)"
)
SUMMARY_HEADER = f"| 과제 | 방식 | {STAT_COLUMNS} |"
TOTALS_HEADER = f"| 제공자 | 모델 | {STAT_COLUMNS} |"


def _group_cells(group: Sequence[RunRow]) -> str:
    """[순수] 실행 묶음의 통계 칸(STAT_COLUMNS 순서, 앞뒤 '|' 없이)."""
    done = [r for r in group if r.status == "completed"]
    times = [r.generate_ms for r in done]
    costs = [r.cost_usd for r in group]
    cost = "-" if any(c is None for c in costs) else f"{sum(c for c in costs if c is not None):.4f}"
    return (
        f"{len(group)} | {len(done)} | "
        f"{_percentile(times, 0.5) if times else '-'} | {_percentile(times, 0.95) if times else '-'} | "
        f"{_mean([r.question_ms for r in group])} | {_mean([r.calls for r in group])} | "
        f"{sum(r.failed_calls for r in group)} | {sum(r.prompt_leaks for r in group)} | "
        f"{_mean([r.input_tokens for r in group])} | {_mean([r.output_tokens for r in group])} | "
        f"{_mean([r.warnings for r in group])} | {sum(r.mismatches for r in group)} | {cost}"
    )


def _table(header: str, groups: Mapping[tuple[str, str], Sequence[RunRow]]) -> str:
    lines = [header, "|" + "---|" * (header.count("|") - 1)]
    lines += [f"| {a} | {b} | {_group_cells(group)} |" for (a, b), group in groups.items()]
    return "\n".join(lines)


def summary_table(rows: Sequence[RunRow]) -> str:
    """[순수] 과제·방식별 요약 표(마크다운). 로드맵 0단계 표에 옮겨 적는다."""
    groups: dict[tuple[str, str], list[RunRow]] = {}
    for row in rows:
        groups.setdefault((row.task, row.variant), []).append(row)
    return _table(SUMMARY_HEADER, groups)


def _models(rows: Sequence[RunRow]) -> str:
    names = {name for row in rows for name in row.models.split(",") if name}
    return ", ".join(sorted(names)) or "-"


def provider_totals(results: Mapping[str, Sequence[RunRow]]) -> str:
    """[순수] 제공자별 전체 합계 표(마크다운). 같은 시나리오를 돈 제공자를 한 줄씩 나란히 둔다."""
    return _table(TOTALS_HEADER, {(name, _models(rows)): rows for name, rows in results.items()})
```

`write_report` 위에 파일 이름 함수를 두고, `write_report`가 결과 글도 쓴다(`return` 바로 앞):

```python
UNSAFE_FILE_CHARS = re.compile(r'[\\/:*?"<>|]')


def document_name(document: RunDocument) -> str:
    """[순수] 결과 글 파일 이름(과제-방식-반복-시나리오.md). 파일 이름에 못 쓰는 글자는 '_'."""
    scenario = UNSAFE_FILE_CHARS.sub("_", document.scenario)
    return f"{document.task}-{document.variant}-{document.repeat}-{scenario}.md"
```

```python
    for document in report.documents:
        docs_dir = out_dir / "documents"
        docs_dir.mkdir(exist_ok=True)
        (docs_dir / document_name(document)).write_text(document.full_text, encoding="utf-8")
```

`write_report` 아래에 비교를 더한다:

```python
def compare(
    *,
    providers: Mapping[str, LLMProvider],
    tasks: Sequence[str],
    repeat: int,
    budget_usd: float | None,
    workdir: Path,
) -> dict[str, MeasureReport]:
    """같은 과제·시나리오를 제공자마다 한 번 호출 방식으로 돈다. 예산은 제공자마다 똑같이 나눈다."""
    share = None if budget_usd is None else budget_usd / len(providers)
    return {
        name: measure(
            tasks=tasks,
            variants=["single"],
            repeat=repeat,
            provider=provider,
            parallel_configs={},
            budget_usd=share,
            workdir=workdir / name,
        )
        for name, provider in providers.items()
    }


def write_comparison(reports: Mapping[str, MeasureReport], out_dir: Path) -> Path:
    """compare.md(제공자별 합계 + 제공자마다 과제별 표)와 제공자별 측정 결과 폴더를 쓴다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = [
        "# 제공자 비교\n\n같은 평가 시나리오를 한 번 호출 방식으로 돌렸다. 시간은 벽시계, 비용은 단가표"
        "(app/harness/measure.py)로 낸 추정이다. 결과 글은 제공자 폴더의 documents/에 있다.",
        "## 합계\n\n" + provider_totals({name: report.rows for name, report in reports.items()}),
    ]
    for name, report in reports.items():
        write_report(report, out_dir / name)
        note = "\n\n예산(제공자 몫)에 닿아 중간에 멈췄다." if report.stopped_by_budget else ""
        parts.append(f"## {name}\n\n{summary_table(report.rows)}{note}")
    path = out_dir / "compare.md"
    path.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return path
```

- [ ] **Step 6: 스크립트**

`scripts/compare_providers.py`:

```python
"""같은 평가 시나리오를 여러 제공자로 돌려 시간·토큰·비용·경고와 결과 글을 나란히 비교한다(TC3).

실행(저장소 루트):
  uv run --directory backend python ../scripts/compare_providers.py --providers mock                # 비용 0, 도구 확인
  uv run --directory backend python ../scripts/compare_providers.py --providers claude openai --budget-usd 5
실제 모델은 비용이 든다. 모델·노력·주소·키(CLAUDE_*·OPENAI_*)는 backend/.env 설정을 따른다.
--budget-usd는 제공자마다 똑같이 나눈다(실제 제공자가 있으면 필수, 추정이다. 콘솔의 사용 한도도 함께 건다).
결과: backend/data/compare/<시각>/compare.md, <제공자>/rows.csv·summary.md·documents/(결과 글)
"""
import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))  # 스크립트 위치와 상관없이 app을 읽는다

from app.config import provider_options, settings  # noqa: E402
from app.harness.measure import compare, provider_totals, write_comparison  # noqa: E402
from app.harness.registry import TASK_TYPES  # noqa: E402
from app.providers.factory import SUPPORTED, get_provider  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="제공자 비교(같은 시나리오, 한 번 호출 방식)")
    parser.add_argument("--providers", nargs="+", choices=list(SUPPORTED), default=["claude", "openai"])
    parser.add_argument("--tasks", nargs="+", choices=TASK_TYPES, default=list(TASK_TYPES))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--budget-usd", type=float, default=None, help="전체 추정 비용 상한(달러, 제공자마다 똑같이 나눈다)")
    parser.add_argument("--out", type=Path, default=None, help="결과 폴더(기본 backend/data/compare/<시각>)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if len(set(args.providers)) != len(args.providers):
        print("같은 제공자를 두 번 넣을 수 없습니다.")
        return 2
    if any(name != "mock" for name in args.providers) and args.budget_usd is None:
        print("실제 모델은 비용이 듭니다. --budget-usd로 상한을 정해 주세요.")
        return 2
    providers = {
        name: get_provider(name, **provider_options(settings.model_copy(update={"provider": name})))
        for name in args.providers
    }
    out = args.out or BACKEND_DIR / "data" / "compare" / datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"제공자 {', '.join(args.providers)} · 과제 {', '.join(args.tasks)} · 반복 {args.repeat}")
    with tempfile.TemporaryDirectory() as workdir:
        reports = compare(
            providers=providers, tasks=args.tasks, repeat=args.repeat, budget_usd=args.budget_usd, workdir=Path(workdir)
        )
    path = write_comparison(reports, out)
    print(provider_totals({name: report.rows for name, report in reports.items()}))
    print(f"저장: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 7: 통과 확인**

Run: `uv run --directory backend pytest tests/test_measure.py tests/test_compare_providers.py -q` → PASS
Run: `uv run --directory backend pytest -q` → 전부 PASS
Run(비용 0): `uv run --directory backend python ../scripts/measure.py --variants single --tasks branding --out data/measure/check` → 표가 나오고 `backend/data/measure/check/documents/`에 결과 글이 생긴다.

- [ ] **Step 8: 커밋**

```bash
git add backend/app/harness/measure.py backend/tests/test_measure.py backend/tests/test_compare_providers.py scripts/compare_providers.py
git commit -m "제공자 비교 도구: 같은 시나리오를 제공자마다 돌려 합계 표·결과 글을 남긴다"
```

---

### Task 2: 실제 비교 실행(승인 뒤)과 문서

컨트롤러가 직접 한다(실제 호출이라 사용자 승인 직후 실행, 결과 해석).

**Files:**
- Create: `docs/PROVIDER-COMPARISON.md` (실행 조건, 합계 표, 과제별 표, 관찰)
- Modify: `docs/test-cases.yaml` (TC3-1 `예정` → `수동` + `manual_result`·`ran_on`, TC3-2 `자동` 추가), `docs/TEST-CASES.xlsx`(스크립트), `docs/WBS.xlsx`(6.14 완료), `docs/HANDOFF.md`, `CLAUDE.md`(측정 줄에 비교 스크립트), `docs/EVALUATION.md`(비교 실험 절에 문서 링크)

- [ ] **Step 1: 승인 받기** — 시나리오 수(과제 5 × 2 = 10, 제공자 2 → 20회), 모델(로컬 설정 `claude-sonnet-5-5`·`gpt-6.1-terra`), 추정 비용, 상한 $5를 보여 주고 승인을 받는다.
- [ ] **Step 2: 실행** — `PYTHONIOENCODING=utf-8 uv run --directory backend python ../scripts/compare_providers.py --providers claude openai --budget-usd 5`
- [ ] **Step 3: 결과 읽기** — `compare.md`, 각 `documents/`(특히 IR 슬라이드 원고가 카드에 실렸는지), `rows.csv`의 `error`.
- [ ] **Step 4: 문서** — `docs/PROVIDER-COMPARISON.md`에 실행일·모델·노력·게이트웨이, 합계 표, 과제별 표, 관찰(완료율·속도·토큰·비용·경고·계획 어긋남·결과 글 품질)을 쓴다. 표에 없는 주장은 하지 않는다.
- [ ] **Step 5: YAML·엑셀·WBS·HANDOFF** — TC3-1(수동, 실제 실행 결과), TC3-2(자동: `backend:tests/test_compare_providers.py::test_compare_runs_same_scenarios_for_every_provider`, `backend:tests/test_compare_providers.py::test_compare_script_with_mock_writes_comparison`). `uv run --directory backend python ../scripts/test_cases.py run`, WBS 6.14 완료, HANDOFF 갱신.
- [ ] **Step 6: 커밋**
