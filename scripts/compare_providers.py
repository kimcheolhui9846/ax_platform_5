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
