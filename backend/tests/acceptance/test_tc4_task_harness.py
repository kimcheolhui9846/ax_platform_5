"""TC4 하네스 파이프라인 과제별 적용: 과제마다 다른 질문·결과 스키마·검증 규칙·질문 상한."""
import pytest

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import SessionState
from app.harness.registry import TASK_TYPES
from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, generate, start
from tests.conftest import api_client


@pytest.fixture(scope="module")
def app():
    return create_app(provider=MockProvider())


@pytest.mark.parametrize("task", TASK_TYPES)
def test_tc4_1_과제마다_자기_정책의_질문을_묻고_자기_스키마로_결과를_낸다(app, task):
    client = api_client(app)
    policy = app.state.registry.get(task).policy
    view, asked = answer_all(client, start(client, task))
    assert asked, "질문이 하나도 없었습니다"
    assert set(asked) <= {f.name for f in policy.fields}
    result = generate(client, view["session_id"])
    app.state.registry.get(task).content_model.model_validate(result["result"]["content"])
    summary = next(s for s in client.get(f"{BASE}/sessions").json() if s["session_id"] == view["session_id"])
    assert summary["title"] == policy.title


@pytest.mark.parametrize(
    ("task", "expected_rules"),
    [
        ("business_plan", {"unsupported_market_claims"}),
        ("marketing_content", {"no_exaggeration"}),
        ("ir_pitch", {"unsupported_investor_claims"}),
        ("branding", {"naming_not_definitive"}),
        ("product_planning", set()),
    ],
)
def test_tc4_2_같은_문장도_과제마다_다른_금지_규칙으로_검사한다(app, task, expected_rules):
    """'예상 매출 100% 무조건'(+ 브랜딩 용어 '이 이름으로 확정')을 과제별 표현 규칙에 넣으면 그 과제 규칙만 걸린다."""
    harness = app.state.registry.get(task)
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    text = "예상 매출 100% 무조건. 이 이름으로 확정"
    result = GenerationResult(sections=sections_from_cards([card]), full_text=text, content={})
    term_rules = {"unsupported_market_claims", "no_exaggeration", "unsupported_investor_claims", "naming_not_definitive"}
    hits = set()
    for check in harness.validators:
        for issue in check(SessionState(task_type=task), result, harness.policy):
            if issue.rule in term_rules:
                hits.add(issue.rule)
    assert hits == expected_rules


@pytest.mark.parametrize("task", TASK_TYPES)
@pytest.mark.parametrize("mode", ["quick", "standard", "precise"])
def test_tc4_3_과제마다_모드별_질문_상한을_지킨다(app, task, mode):
    """모든 모드는 상한 이하, 빠른 모드는 상한(3)을 정확히 채운다(다른 모드는 준비도가 차면 상한 전에 멈춘다)."""
    client = api_client(app)
    cap = app.state.registry.get(task).policy.question_caps[mode]
    _, asked = answer_all(client, start(client, task, mode=mode))
    assert len(set(asked)) <= cap
    if mode == "quick":
        assert len(set(asked)) == cap, f"빠른 모드는 상한 {cap}개를 모두 물어야 합니다: {asked}"
