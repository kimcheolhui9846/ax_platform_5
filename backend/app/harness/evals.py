"""과제 폴더 evals/*.yaml 시나리오를 하네스에 돌린다.

하네스를 고친 뒤 회귀 확인에 쓰고, 나중에 실제 모델이 붙으면 같은 시나리오로 품질을 비교한다.
"""
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.state import Answer, AnswerType, CoachingMode, Question, SessionState, SessionStatus
from app.harness.base import BaseHarness
from app.harness.errors import GenerationFailed
from app.harness.policy import FieldKind, TaskPolicy


class ScenarioAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_type: AnswerType = AnswerType.FREE_TEXT
    value: str | None = None
    option_indexes: list[int] = Field(default_factory=list)  # 0부터 센 선택지 위치


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    raw_input: str
    mode: CoachingMode = CoachingMode.STANDARD
    answers: dict[str, list[ScenarioAnswer]] = Field(default_factory=dict)  # 필드별로 차례대로 쓸 답변
    expect_status: SessionStatus = SessionStatus.COMPLETED


def load_scenarios(task_dir: Path) -> list[Scenario]:
    scenarios = []
    for path in sorted((task_dir / "evals").glob("*.yaml")):
        with path.open(encoding="utf-8") as fp:
            scenarios.append(Scenario.model_validate(yaml.safe_load(fp)))
    return scenarios


def build_answer(question: Question, planned: ScenarioAnswer) -> Answer:
    """[코드·순수] 시나리오의 계획된 답을 질문에 대한 Answer로 바꾼다."""
    bad = [i for i in planned.option_indexes if not 0 <= i < len(question.options)]
    if bad:
        raise ValueError(
            f"필드 '{question.field}' 질문의 선택지는 {len(question.options)}개인데 "
            f"시나리오가 {bad}번을 골랐습니다."
        )
    return Answer(
        question_id=question.question_id,
        answer_type=planned.answer_type,
        value=planned.value,
        option_ids=[question.options[i].id for i in planned.option_indexes],
    )


def unknown_answer_fields(scenario: Scenario, policy: TaskPolicy) -> list[str]:
    """[코드·순수] answers 키 중 물을 수 있는 필드(kind가 default가 아닌 policy 필드)가 아닌 것."""
    askable = {f.name for f in policy.fields if f.kind is not FieldKind.DEFAULT}
    return [name for name in scenario.answers if name not in askable]


def run_scenario(harness: BaseHarness, scenario: Scenario, max_turns: int = 50) -> SessionState:
    """시나리오에 없는 질문은 건너뛰고, 질문이 끝나면 결과를 생성한다.

    계획한 답은 모두 쓰여야 한다. 모르는 필드에 답을 계획했거나 끝까지 쓰이지 않은 답이 남으면
    시나리오가 하네스 흐름과 어긋난 것이므로 시나리오 이름과 함께 실패한다.
    생성 실패는 예외가 아니라 FAILED 상태로 돌려준다(expect_status: failed 시나리오).
    """
    unknown = unknown_answer_fields(scenario, harness.policy)
    if unknown:
        raise ValueError(
            f"시나리오 '{scenario.name}'의 answers에 물을 수 있는 필드가 아닌 키가 있습니다: {', '.join(unknown)}"
        )
    state = harness.start(scenario.raw_input, scenario.mode)
    queues = {name: list(answers) for name, answers in scenario.answers.items()}
    for _ in range(max_turns):
        question = state.pending_question
        if question is None:
            break
        queue = queues.get(question.field)
        planned = queue.pop(0) if queue else ScenarioAnswer(answer_type=AnswerType.SKIP)
        try:
            answer = build_answer(question, planned)
        except ValueError as exc:
            raise ValueError(f"시나리오 '{scenario.name}': {exc}") from exc
        harness.apply_answer(state, answer)
    else:
        raise RuntimeError(f"시나리오 '{scenario.name}'가 {max_turns}턴 안에 끝나지 않았습니다.")
    leftover = [f"{name}({len(queue)}개)" for name, queue in queues.items() if queue]
    if leftover:
        raise ValueError(f"시나리오 '{scenario.name}'에서 쓰이지 않은 답변이 남았습니다: {', '.join(leftover)}")
    try:
        harness.generate(state)
    except GenerationFailed:
        pass  # state는 FAILED로 표시돼 있다
    return state
