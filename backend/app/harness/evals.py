"""과제 폴더 evals/*.yaml 시나리오를 하네스에 돌린다.

하네스를 고친 뒤 회귀 확인에 쓰고, 나중에 실제 모델이 붙으면 같은 시나리오로 품질을 비교한다.
"""
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.core.state import Answer, AnswerType, CoachingMode, Question, SessionState, SessionStatus
from app.harness.base import BaseHarness


class ScenarioAnswer(BaseModel):
    answer_type: AnswerType = AnswerType.FREE_TEXT
    value: str | None = None
    option_indexes: list[int] = Field(default_factory=list)  # 0부터 센 선택지 위치


class Scenario(BaseModel):
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


def run_scenario(harness: BaseHarness, scenario: Scenario, max_turns: int = 50) -> SessionState:
    """시나리오에 없는 질문은 건너뛰고, 질문이 끝나면 결과를 생성한다."""
    state = harness.start(scenario.raw_input, scenario.mode)
    queues = {name: list(answers) for name, answers in scenario.answers.items()}
    for _ in range(max_turns):
        question = state.pending_question
        if question is None:
            break
        queue = queues.get(question.field)
        planned = queue.pop(0) if queue else ScenarioAnswer(answer_type=AnswerType.SKIP)
        harness.apply_answer(state, build_answer(question, planned))
    else:
        raise RuntimeError(f"시나리오 '{scenario.name}'가 {max_turns}턴 안에 끝나지 않았습니다.")
    harness.generate(state)
    return state
