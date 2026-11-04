"""테스트 케이스 문서: 원본 docs/test-cases.yaml → docs/TEST-CASES.xlsx.

  build  결과 칸을 비운 엑셀을 만든다
  run    자동 테스트를 실제로 돌려 실제 결과·통과·실행일을 채운다

uv run --directory backend python ../scripts/test_cases.py run
"""
import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "test-cases.yaml"
OUTPUT = ROOT / "docs" / "TEST-CASES.xlsx"
HEADER = ["ID", "요구사항", "테스트 케이스", "사전 조건", "절차", "기대 결과", "방식", "자동 테스트 위치", "실제 결과", "통과", "실행일", "비고"]
WIDTHS = [9, 22, 34, 26, 48, 40, 7, 52, 10, 7, 12, 30]


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    group: str
    item: str
    title: str
    precondition: str = ""
    steps: list[str] = Field(min_length=1)
    expected: str
    method: Literal["자동", "수동", "예정"]
    tests: list[str] = Field(default_factory=list)
    note: str = ""
    manual_result: Literal["통과", "실패"] | None = None
    ran_on: str | None = None

    @model_validator(mode="after")
    def _manual_result_only_for_manual(self) -> "Case":
        if (self.manual_result is None) != (self.ran_on is None):
            raise ValueError(f"{self.id}: manual_result와 ran_on은 함께 적어야 합니다")
        if self.manual_result is not None and self.method != "수동":
            raise ValueError(f"{self.id}: manual_result는 수동 케이스에만 적습니다")
        return self

    @model_validator(mode="after")
    def _tests_match_method(self) -> "Case":
        if self.method == "자동" and not self.tests:
            raise ValueError(f"{self.id}: 자동 케이스에는 tests가 필요합니다")
        if self.method != "자동" and self.tests:
            raise ValueError(f"{self.id}: 수동·예정 케이스에는 tests를 적지 않습니다")
        return self


def load_cases(path: Path) -> list[Case]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = [Case.model_validate(c) for c in data["cases"]]
    ids = [c.id for c in cases]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"테스트 케이스 ID가 중복됩니다: {', '.join(repeated)}")
    return cases


def case_results(cases: list[Case], outcomes: dict[str, bool]) -> dict[str, str]:
    """[순수] 참조 테스트가 모두 통과면 '통과', 하나라도 실패·없음이면 '실패'. 자동 케이스만."""
    return {
        c.id: "통과" if all(outcomes.get(ref, False) for ref in c.tests) else "실패"
        for c in cases
        if c.method == "자동"
    }


def build(cases: list[Case], results: dict[str, str], ran_on: str | None, out: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "테스트 케이스"
    sheet.append(HEADER)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for c in cases:
        result = results.get(c.id, "")
        row_ran_on = ran_on if result else ""
        if c.method == "수동" and c.manual_result is not None:
            result, row_ran_on = c.manual_result, c.ran_on
        sheet.append([
            c.id, c.item, c.title, c.precondition,
            "\n".join(f"{i}. {s}" for i, s in enumerate(c.steps, 1)),
            c.expected, c.method, "\n".join(c.tests),
            result, "O" if result == "통과" else ("X" if result == "실패" else ""),
            row_ran_on, c.note,
        ])
    for i, width in enumerate(WIDTHS, 1):
        sheet.column_dimensions[sheet.cell(1, i).column_letter].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"
    book.save(out)


def _backend_outcomes(refs: list[str], tmp: Path) -> dict[str, bool]:
    """backend 참조 → 통과 여부. 보고서가 없으면(pytest가 못 돌았으면) 모두 실패."""
    if not refs:
        return {}
    report = tmp / "backend.xml"
    files = sorted({r.removeprefix("backend:").split("::")[0] for r in refs})
    subprocess.run(["uv", "run", "--directory", str(ROOT / "backend"), "pytest", *files, f"--junitxml={report}", "-q"], check=False)
    if not report.exists():
        print("backend 테스트 보고서가 없습니다. backend 자동 테스트를 모두 실패로 처리합니다.", file=sys.stderr)
        return {r: False for r in refs}
    passed: dict[tuple[str, str], bool] = {}
    for case in ET.parse(report).iter("testcase"):
        stem = case.get("classname", "").split(".")[-1]
        key = (stem, case.get("name", "").split("[")[0])
        ok = not any(child.tag in ("failure", "error", "skipped") for child in case)
        passed[key] = passed.get(key, True) and ok

    def key_of(ref: str) -> tuple[str, str]:
        file, name = ref.removeprefix("backend:").split("::")
        return Path(file).stem, name.split("[")[0]

    return {r: passed.get(key_of(r), False) for r in refs}


def _frontend_outcomes(refs: list[str], tmp: Path) -> dict[str, bool]:
    """frontend 참조 → 통과 여부. 보고서가 없으면(vitest가 못 돌았으면) 모두 실패."""
    if not refs:
        return {}
    report = tmp / "frontend.json"
    files = sorted({r.removeprefix("frontend:").split("::")[0] for r in refs})
    subprocess.run(
        ["npm", "--prefix", str(ROOT / "frontend"), "exec", "--", "vitest", "run", *files, "--reporter=json", f"--outputFile={report}"],
        check=False, shell=sys.platform == "win32", cwd=ROOT / "frontend",
    )
    if not report.exists():
        print("frontend 테스트 보고서가 없습니다. frontend 자동 테스트를 모두 실패로 처리합니다.", file=sys.stderr)
        return {r: False for r in refs}
    data = json.loads(report.read_text(encoding="utf-8"))
    passed = {
        a["title"]: a["status"] == "passed"
        for result in data["testResults"]
        for a in result["assertionResults"]
    }
    return {r: passed.get(r.split("::")[1], False) for r in refs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "run"])
    args = parser.parse_args()
    cases = load_cases(SOURCE)
    if args.command == "build":
        build(cases, {}, None, OUTPUT)
    else:
        refs = [r for c in cases for r in c.tests]
        with tempfile.TemporaryDirectory() as tmp:
            outcomes = {
                **_backend_outcomes([r for r in refs if r.startswith("backend:")], Path(tmp)),
                **_frontend_outcomes([r for r in refs if r.startswith("frontend:")], Path(tmp)),
            }
        results = case_results(cases, outcomes)
        build(cases, results, date.today().isoformat(), OUTPUT)
        failed = [case_id for case_id, result in results.items() if result == "실패"]
        print(f"저장: {OUTPUT.relative_to(ROOT)}")
        if failed:
            print(f"실패한 자동 케이스: {', '.join(failed)}", file=sys.stderr)
            sys.exit(1)
        return
    print(f"저장: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
