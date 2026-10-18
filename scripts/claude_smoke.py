"""실제 Claude로 세션 하나를 끝까지 돌려 본다(비용 발생). 키는 환경 변수 ANTHROPIC_API_KEY.

실행(저장소 루트): uv run --directory backend python ../scripts/claude_smoke.py [과제] [요청 글]
  예) uv run --directory backend python ../scripts/claude_smoke.py product_planning "집들이 선물용 수제 향초"
진단 → 질문 하나에 '아직 모르겠어요' → 생성까지 돌리고, 단계별 모델·토큰과 결과 섹션 제목을 출력한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # 스크립트 위치와 상관없이 app을 읽는다

from app.config import settings  # noqa: E402
from app.core.state import Answer, AnswerType  # noqa: E402
from app.harness.errors import GenerationFailed  # noqa: E402
from app.harness.registry import build_harness  # noqa: E402
from app.providers.claude import ClaudeProvider  # noqa: E402

DEFAULT_TASK = "product_planning"
DEFAULT_REQUEST = "집들이 선물용 수제 향초"


def print_trace(trace) -> None:
    """단계마다 제공자·모델·토큰만 한 줄씩. 프롬프트와 응답 내용은 출력하지 않는다."""
    for entry in trace:
        print(f"- {entry.stage}: provider={entry.provider} model={entry.model} usage={entry.usage}")


def main(argv: list[str]) -> int:
    task = argv[1] if len(argv) > 1 else DEFAULT_TASK
    raw = argv[2] if len(argv) > 2 else DEFAULT_REQUEST
    print(f"과제 {task} · 모델 {settings.claude_model} · 노력 {settings.claude_effort}")
    harness = build_harness(task, ClaudeProvider(settings.claude_model, settings.claude_effort))
    state = harness.start(raw)
    if state.pending_question is not None:
        harness.apply_answer(state, Answer(question_id=state.pending_question.question_id, answer_type=AnswerType.SKIP))
    try:
        harness.generate(state)
    except GenerationFailed:
        print_trace(state.trace)
        print(f"생성 실패: {state.trace[-1].output.get('error')}")
        return 1
    print_trace(state.trace)
    print("결과 섹션:")
    for section in state.result.sections:
        print(f"  {section.order}. {section.heading}")
    print(f"검증 이슈 {len(state.validation.issues)}개 · 상태 {state.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
