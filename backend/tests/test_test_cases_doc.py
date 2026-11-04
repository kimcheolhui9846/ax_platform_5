"""테스트 케이스 문서 원본(docs/test-cases.yaml)이 형식대로이고, 적힌 자동 테스트가 실제로 있다."""
import ast
import importlib.util
import re
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


IT_TITLE = re.compile(r"""\bit\(\s*(["'`])(.+?)\1""")


def frontend_titles(path: Path) -> list[str]:
    return [m.group(2) for m in IT_TITLE.finditer(path.read_text(encoding="utf-8"))]


def test_frontend_references_point_to_existing_test_titles():
    for case in CASES:
        for ref in case.tests:
            side, target = ref.split(":", 1)
            if side != "frontend":
                continue
            file, title = target.split("::")
            path = ROOT / "frontend" / file
            assert path.exists(), f"{case.id}: {file} 없음"
            titles = frontend_titles(path)
            assert title in titles, f"{case.id}: it('{title}') 없음"
            assert titles.count(title) == 1, f"{case.id}: '{title}' 제목이 {file}에 중복됩니다"


def test_frontend_references_are_unique():
    refs = [ref for case in CASES for ref in case.tests if ref.startswith("frontend:")]
    assert len(refs) == len(set(refs))


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


def manual_case(**extra):
    return {
        "id": "TCX-1", "group": "TCX", "item": "i", "title": "t", "steps": ["s"], "expected": "e",
        "method": "수동", **extra,
    }


def test_manual_result_only_allowed_on_manual_cases():
    import pytest

    with pytest.raises(ValueError, match="수동"):
        script.Case.model_validate(
            manual_case(method="자동", tests=["backend:x.py::t"], manual_result="통과", ran_on="2026-11-04")
        )


def test_manual_result_and_ran_on_come_together():
    import pytest

    with pytest.raises(ValueError, match="함께"):
        script.Case.model_validate(manual_case(manual_result="통과"))


def test_build_writes_manual_case_result(tmp_path):
    from openpyxl import load_workbook

    case = script.Case.model_validate(manual_case(manual_result="통과", ran_on="2026-11-04"))
    out = tmp_path / "tc.xlsx"
    script.build([case], {}, None, out)
    row = [c.value for c in load_workbook(out)["테스트 케이스"][2]]
    assert row[script.HEADER.index("실제 결과")] == "통과"
    assert row[script.HEADER.index("통과")] == "O"
    assert row[script.HEADER.index("실행일")] == "2026-11-04"


def test_spreadsheet_rows_match_yaml_case_ids_in_order():
    """엑셀을 다시 만들지 않고 제출하는 일을 막는다."""
    from openpyxl import load_workbook

    sheet = load_workbook(ROOT / "docs" / "TEST-CASES.xlsx")["테스트 케이스"]
    ids = [row[0].value for row in sheet.iter_rows(min_row=2) if row[0].value]
    assert ids == [c.id for c in CASES]
