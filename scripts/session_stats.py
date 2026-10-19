"""저장된 세션으로 평가 지표(기획서 14장 중 앱 기록으로 셀 수 있는 것)를 과제별 표로 낸다. 비용 0(AI를 부르지 않는다).

실행(저장소 루트): uv run --directory backend python ../scripts/session_stats.py [--db 경로]
기본은 backend/.env의 DATABASE_PATH(SQLite)다. 사용성 테스트는 STORE=sqlite로 띄운 로컬 서버에서 하고 끝나면 이 표를 본다.
지표의 뜻과 한계는 docs/EVALUATION.md.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # 스크립트 위치와 상관없이 app을 읽는다

from app.config import settings  # noqa: E402
from app.core.store import SqliteSessionStore  # noqa: E402
from app.harness.policy import FieldKind  # noqa: E402
from app.harness.registry import TASK_TYPES, build_harness  # noqa: E402
from app.harness.stats import metrics_table, session_metrics  # noqa: E402
from app.providers.mock import MockProvider  # noqa: E402


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="저장된 세션의 평가 지표(비용 0)")
    parser.add_argument("--db", type=Path, default=settings.database_path, help="SQLite 세션 파일")
    args = parser.parse_args(argv)
    if not args.db.exists():
        print(f"세션 파일이 없습니다: {args.db} (STORE=sqlite로 서버를 띄워 사용한 뒤 실행하세요)")
        return 1
    must_confirm = {
        task: frozenset(f.name for f in build_harness(task, MockProvider()).policy.fields if f.kind is FieldKind.MUST_CONFIRM)
        for task in TASK_TYPES
    }
    states = SqliteSessionStore(args.db).list_all()
    print(f"세션 {len(states)}개 · {args.db}")
    print(metrics_table(session_metrics(states, must_confirm)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
