"""측정: 평가 시나리오(evals/*.yaml)를 방식(한 번 호출·병렬)별로 돌려 시간·토큰·실패·경고·비용을 표로 낸다.

docs/HARNESS-ROADMAP.md 0단계 표를 채우는 도구다. 실행은 scripts/measure.py. 제공자를 받기만 하므로 Mock이면 비용 0이고,
실제 모델이면 비용이 든다(budget_usd로 누적 추정 비용 상한을 건다). 실제 모델은 질문 순서가 달라 시나리오 계획이
어긋날 수 있어 실패 대신 어긋남 수(mismatches)로 센다(evals.play_questions).
"""
import csv
import math
import re
import shutil
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.core.state import SessionState
from app.harness.base import BaseHarness
from app.harness.evals import load_scenarios, play_questions
from app.harness.policy import ParallelGeneration
from app.harness.registry import TASKS_DIR, build_harness, harness_class
from app.providers.base import LLMProvider

MEASURE_PARALLEL_PATH = Path(__file__).resolve().parents[3] / "scripts" / "measure_parallel.yaml"
VARIANTS = ("single", "parallel")

# 1M 토큰당 (입력, 출력) 달러. docs/HANDOFF.md의 참고 단가와 같게 둔다. 캐시 읽기·쓰기는 입력 단가의 배수다.
# GPT는 BAZE 게이트웨이 단가(GET /v1/gateway/models/)다. 캐시 읽기 배수는 모델마다 조금 달라 추정이다.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "gpt-6.1-sol": (2.0, 10.0),
    "gpt-6.1-terra": (1.0, 5.0),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-5.6-luna": (0.20, 1.20),
}
CACHE_READ_RATE = 0.1
CACHE_WRITE_RATE = 1.25


class RunRow(BaseModel):
    """시나리오 한 번 실행의 결과(CSV 한 줄)."""

    task: str
    scenario: str
    variant: str
    repeat: int
    status: str  # 세션 상태(completed·failed 등) 또는 error(예외로 끝남)
    question_ms: int = 0  # 질문 단계 벽시계 시간
    generate_ms: int = 0  # 생성 벽시계 시간(병렬이면 가장 느린 조각 + 합치기)
    calls: int = 0  # 실제로 제공자를 부른 수(캐시·요약 제외)
    failed_calls: int = 0  # 그중 실패(형식·잘림·거절·유출 차단 포함)
    prompt_leaks: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    warnings: int = 0  # 검증 경고 수
    mismatches: int = 0  # 시나리오 계획과 어긋난 곳
    models: str = ""  # 응답한 모델 id(쉼표)
    cost_usd: float | None = 0.0  # 추정 비용. 단가를 모르는 모델이 섞이면 None
    error: str = ""


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


def _price(model: str) -> tuple[float, float] | None:
    if model.startswith("mock"):  # Mock 제공자(LLM·이미지)는 비용 0
        return (0.0, 0.0)
    for name, price in PRICES_PER_MTOK.items():
        if model.startswith(name):
            return price
    return None


def call_cost(model: str | None, usage: Mapping[str, int]) -> float | None:
    """[순수] 호출 한 번의 추정 비용(달러). 응답이 없으면(실패) 0, 단가를 모르는 모델이면 None."""
    if model is None:
        return 0.0
    price = _price(model)
    if price is None:
        return None
    inp, out = price
    return (
        usage.get("input_tokens", 0) * inp
        + usage.get("output_tokens", 0) * out
        + usage.get("cache_read_input_tokens", 0) * inp * CACHE_READ_RATE
        + usage.get("cache_creation_input_tokens", 0) * inp * CACHE_WRITE_RATE
    ) / 1_000_000


def summarize(
    task: str,
    scenario: str,
    variant: str,
    repeat: int,
    state: SessionState | None,
    *,
    mismatches: Sequence[str],
    question_ms: int,
    generate_ms: int,
    error: str,
) -> RunRow:
    """[순수] 세션 trace에서 실행 한 줄을 만든다. 제공자를 부른 기록은 duration_ms가 있는 항목이다."""
    trace = state.trace if state is not None else []
    calls = [t for t in trace if t.duration_ms is not None]
    costs = [call_cost(t.model, t.usage) for t in calls]
    return RunRow(
        task=task,
        scenario=scenario,
        variant=variant,
        repeat=repeat,
        status="error" if error else (state.status.value if state is not None else "error"),
        question_ms=question_ms,
        generate_ms=generate_ms,
        calls=len(calls),
        failed_calls=sum(1 for t in calls if "error" in t.output),
        prompt_leaks=sum(1 for t in calls if t.output.get("error") == "prompt_leak"),
        input_tokens=sum(t.usage.get("input_tokens", 0) for t in calls),
        output_tokens=sum(t.usage.get("output_tokens", 0) for t in calls),
        cache_read_tokens=sum(t.usage.get("cache_read_input_tokens", 0) for t in calls),
        cache_write_tokens=sum(t.usage.get("cache_creation_input_tokens", 0) for t in calls),
        warnings=len(state.validation.issues) if state is not None and state.validation is not None else 0,
        mismatches=len(mismatches),
        models=",".join(sorted({t.model for t in calls if t.model})),
        cost_usd=None if any(c is None for c in costs) else sum(c for c in costs if c is not None),
        error=error,
    )


def load_parallel_configs(path: Path) -> dict[str, ParallelGeneration]:
    with path.open(encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    return {task: ParallelGeneration.model_validate(config) for task, config in data.items()}


def variant_harness(
    task: str, variant: str, provider: LLMProvider, parallel_configs: Mapping[str, ParallelGeneration], workdir: Path
) -> BaseHarness:
    """방식별 하네스. parallel은 과제 폴더를 workdir에 복사해 그 정책에만 조각을 붙인다(실제 정책은 그대로)."""
    if variant == "single":
        return build_harness(task, provider)
    if variant != "parallel":
        raise ValueError(f"모르는 방식입니다: {variant} (가능: {', '.join(VARIANTS)})")
    if task not in parallel_configs:
        raise ValueError(f"{task}의 병렬 조각이 {MEASURE_PARALLEL_PATH.name}에 없습니다.")
    target = workdir / task
    if not target.exists():
        shutil.copytree(TASKS_DIR / task, target, ignore=shutil.ignore_patterns("__pycache__"))
        extra = {"parallel_generation": parallel_configs[task].model_dump()}
        with (target / "policy.yaml").open("a", encoding="utf-8") as fp:
            fp.write("\n" + yaml.safe_dump(extra, allow_unicode=True, sort_keys=False))
    return harness_class(task)(target, provider)


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


def run_once(
    harness: BaseHarness, scenario_name: str, scenario, variant: str, repeat: int
) -> tuple[RunRow, RunDocument | None]:
    """시나리오 한 번. 질문 단계와 생성의 벽시계 시간을 따로 잰다. 예외는 기록하고 다음 실행으로 넘어간다."""
    state, mismatches, question_ms, generate_ms, error = None, [], 0, 0, ""
    started = time.perf_counter()
    try:
        played = play_questions(harness, scenario)
        state, mismatches = played.state, played.mismatches
        question_ms = _elapsed_ms(started)
        started = time.perf_counter()
        try:
            harness.generate(state)
        finally:
            generate_ms = _elapsed_ms(started)
    except Exception as exc:  # noqa: BLE001 — 측정은 실패도 한 줄로 남기고 계속한다
        if state is None or state.status.value != "failed":
            error = f"{type(exc).__name__}: {exc}"
        if not question_ms:
            question_ms = _elapsed_ms(started)
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


def measure(
    *,
    tasks: Sequence[str],
    variants: Sequence[str],
    repeat: int,
    provider: LLMProvider,
    parallel_configs: Mapping[str, ParallelGeneration],
    budget_usd: float | None,
    workdir: Path,
) -> MeasureReport:
    """과제 × 시나리오 × 방식 × 반복을 돈다. 누적 추정 비용이 budget_usd에 닿으면 다음 실행부터 멈춘다."""
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


def _percentile(values: Sequence[int], q: float) -> int:
    """[순수] 최근접 순위 백분위수."""
    ordered = sorted(values)
    return ordered[max(math.ceil(q * len(ordered)) - 1, 0)]


def _mean(values: Sequence[float]) -> str:
    return f"{sum(values) / len(values):.1f}" if values else "-"


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


UNSAFE_FILE_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
SCENARIO_NAME_LIMIT = 60  # 파일 이름이 너무 길어지지 않게


def document_name(document: RunDocument) -> str:
    """[순수] 결과 글 파일 이름(과제-방식-반복-시나리오.md). 파일 이름에 못 쓰는 글자(제어 문자 포함)는 '_',
    시나리오 이름은 앞 60자까지, 끝의 점·공백은 뺀다(Windows가 거부한다)."""
    scenario = UNSAFE_FILE_CHARS.sub("_", document.scenario)[:SCENARIO_NAME_LIMIT].rstrip(". ")
    return f"{document.task}-{document.variant}-{document.repeat}-{scenario}.md"


def write_report(report: MeasureReport, out_dir: Path) -> tuple[Path, Path]:
    """rows.csv(실행마다 한 줄)와 summary.md(요약 표)를 쓴다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path, summary_path = out_dir / "rows.csv", out_dir / "summary.md"
    with rows_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(RunRow.model_fields))
        writer.writeheader()
        for row in report.rows:
            writer.writerow(row.model_dump())
    note = "\n\n누적 추정 비용이 상한(--budget-usd)에 닿아 중간에 멈췄다.\n" if report.stopped_by_budget else "\n"
    summary_path.write_text(
        "# 측정 요약\n\n시간은 벽시계 기준, 비용은 단가표(app/harness/measure.py)로 낸 추정이다. "
        "Mock의 토큰 수는 글자 수다.\n\n" + summary_table(report.rows) + note,
        encoding="utf-8",
    )
    docs_dir = out_dir / "documents"
    if report.documents:
        docs_dir.mkdir(exist_ok=True)
    for document in report.documents:
        (docs_dir / document_name(document)).write_text(document.full_text, encoding="utf-8")
    return rows_path, summary_path


def compare(
    *,
    providers: Mapping[str, LLMProvider],
    tasks: Sequence[str],
    repeat: int,
    budget_usd: float | None,
    workdir: Path,
) -> dict[str, MeasureReport]:
    """같은 과제·시나리오를 제공자마다 한 번 호출 방식으로 돈다. 예산은 제공자마다 똑같이 나눈다."""
    if not providers:
        raise ValueError("비교할 제공자가 없습니다.")
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
