"""저장된 세션으로 평가 지표(기획서 14장 중 앱 기록으로 셀 수 있는 것)를 과제별 표로 낸다. 비용 0(AI를 부르지 않는다).

실행(저장소 루트): uv run --directory backend python ../scripts/session_stats.py [--db 경로]
기본은 backend/.env의 STORE(sqlite면 DATABASE_PATH 파일, postgres면 DATABASE_URL)다. --db를 주면 그 SQLite 파일을 읽는다. 사용성 테스트는 STORE=sqlite로 띄운 로컬 서버에서 하고 끝나면 이 표를 본다.
지표의 뜻과 한계는 docs/EVALUATION.md.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # 스크립트 위치와 상관없이 app을 읽는다

from app.config import settings  # noqa: E402
from app.core.storage import read_all_sessions  # noqa: E402
from app.harness.policy import FieldKind  # noqa: E402
from app.harness.registry import TASK_TYPES, build_harness  # noqa: E402
from app.harness.stats import metrics_table, session_metrics  # noqa: E402
from app.providers.mock import MockProvider  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="저장된 세션의 평가 지표(비용 0)")
    parser.add_argument("--db", type=Path, default=None, help="SQLite 세션 파일(주면 STORE 설정 대신 이 파일을 읽는다)")
    args = parser.parse_args(argv)
    if args.db is not None:
        kind, path, url = "sqlite", args.db, None
    else:
        kind, path = settings.store, settings.database_path
        url = settings.database_url.get_secret_value() if settings.database_url else None
    if kind == "sqlite" and not path.exists():
        print(f"세션 파일이 없습니다: {path} (STORE=sqlite로 서버를 띄워 사용한 뒤 실행하세요)")
        return 1
    if kind == "memory":
        print("STORE=memory는 남는 세션이 없습니다. STORE=sqlite 또는 postgres로 설정하세요.")
        return 1
    must_confirm = {
        task: frozenset(f.name for f in build_harness(task, MockProvider()).policy.fields if f.kind is FieldKind.MUST_CONFIRM)
        for task in TASK_TYPES
    }
    states = read_all_sessions(kind, path, settings.asset_dir, url)
    print(f"세션 {len(states)}개 · {path if kind == 'sqlite' else 'postgres'}")
    print(metrics_table(session_metrics(states, must_confirm)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
