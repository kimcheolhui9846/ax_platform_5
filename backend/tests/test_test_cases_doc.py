"""테스트 케이스 문서 원본(docs/test-cases.yaml)이 형식대로이고, 적힌 자동 테스트가 실제로 있다."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("test_cases_script", ROOT / "scripts" / "test_cases.py")
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)

CASES = script.load_cases(ROOT / "docs" / "test-cases.yaml")


def test_every_requirement_group_is_present():
    assert {c.group for c in CASES} == {f"TC{n}" for n in range(1, 9)}


def test_backend_references_point_to_defined_tests():
    for case in CASES:
        for ref in case.tests:
            side, target = ref.split(":", 1)
            if side != "backend":
                continue
            file, name = target.split("::")
            path = ROOT / "backend" / file
            assert path.exists(), f"{case.id}: {file} 없음"
            names = {n.name for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef)}
            assert name.split("[")[0] in names, f"{case.id}: {name} 없음"


def test_frontend_references_point_to_existing_test_titles():
    for case in CASES:
        for ref in case.tests:
            side, target = ref.split(":", 1)
            if side != "frontend":
                continue
            file, title = target.split("::")
            path = ROOT / "frontend" / file
            assert path.exists(), f"{case.id}: {file} 없음"
            assert title in path.read_text(encoding="utf-8"), f"{case.id}: '{title}' 없음"


def test_case_results_fail_if_any_reference_fails():
    cases = [c for c in CASES if c.tests][:1]
    ok = {ref: True for ref in cases[0].tests}
    assert script.case_results(cases, ok) == {cases[0].id: "통과"}
    bad = {**ok, cases[0].tests[0]: False}
    assert script.case_results(cases, bad) == {cases[0].id: "실패"}


def test_build_writes_header_and_one_row_per_case(tmp_path):
    from openpyxl import load_workbook

    out = tmp_path / "tc.xlsx"
    script.build(CASES, {}, None, out)
    sheet = load_workbook(out)["테스트 케이스"]
    header = [c.value for c in sheet[1]]
    assert header[:3] == ["ID", "요구사항", "테스트 케이스"]
    assert sheet.max_row == len(CASES) + 1
