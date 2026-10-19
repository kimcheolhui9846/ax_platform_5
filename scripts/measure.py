"""평가 시나리오를 돌려 시간·토큰·실패·경고·비용을 잰다(docs/HARNESS-ROADMAP.md 0단계). 기본은 Mock이라 비용 0이다.

실행(저장소 루트):
  uv run --directory backend python ../scripts/measure.py                         # Mock, 모든 과제, 한 번 호출·병렬
  uv run --directory backend python ../scripts/measure.py --provider claude --budget-usd 2 --repeat 3
실제 모델(--provider claude)은 비용이 든다. 키는 환경 변수 ANTHROPIC_API_KEY, 모델·노력·단계별 라우팅은 backend/.env 설정을 따른다.
--budget-usd는 누적 추정 비용이 그 값에 닿으면 다음 실행부터 멈춘다(추정이다. 콘솔의 사용 한도도 함께 건다).
결과: backend/data/measure/<시각>/rows.csv(실행마다 한 줄), summary.md(과제·방식별 요약 표).
"""
import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))  # 스크립트 위치와 상관없이 app을 읽는다

from app.config import settings  # noqa: E402
from app.harness.measure import (  # noqa: E402
    MEASURE_PARALLEL_PATH,
    VARIANTS,
    load_parallel_configs,
    measure,
    summary_table,
    write_report,
)
from app.harness.registry import TASK_TYPES  # noqa: E402
from app.providers.factory import get_provider  # noqa: E402


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="하네스 측정(기본 Mock, 비용 0)")
    parser.add_argument("--provider", choices=["mock", "claude"], default="mock")
    parser.add_argument("--tasks", nargs="+", choices=TASK_TYPES, default=list(TASK_TYPES))
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--budget-usd", type=float, default=None, help="누적 추정 비용 상한(달러)")
    parser.add_argument("--out", type=Path, default=None, help="결과 폴더(기본 backend/data/measure/<시각>)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.provider == "claude" and args.budget_usd is None:
        print("실제 모델은 비용이 듭니다. --budget-usd로 상한을 정해 주세요.")
        return 2
    provider = get_provider(
        args.provider,
        model=settings.claude_model,
        effort=settings.claude_effort,
        stage_models=settings.claude_stage_models,
        stage_efforts=settings.claude_stage_efforts,
    )
    out = args.out or BACKEND_DIR / "data" / "measure" / datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"제공자 {args.provider} · 과제 {', '.join(args.tasks)} · 방식 {', '.join(args.variants)} · 반복 {args.repeat}")
    with tempfile.TemporaryDirectory() as workdir:
        report = measure(
            tasks=args.tasks,
            variants=args.variants,
            repeat=args.repeat,
            provider=provider,
            parallel_configs=load_parallel_configs(MEASURE_PARALLEL_PATH),
            budget_usd=args.budget_usd,
            workdir=Path(workdir),
        )
    rows_path, summary_path = write_report(report, out)
    print(summary_table(report.rows))
    if report.stopped_by_budget:
        print("누적 추정 비용이 상한에 닿아 중간에 멈췄습니다.")
    print(f"저장: {rows_path}\n      {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
