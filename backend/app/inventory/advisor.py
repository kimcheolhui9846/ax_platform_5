"""AI 보충 기준 추천. 계산·주문 판단은 코드가 하고 AI는 최소·목표·구매 단위와 이유만 낸다(확인 전).

외부로 나가는 프롬프트는 코칭과 같은 규칙을 따른다: 바깥 값은 | inline으로 감싸고, system에 _untrusted.md를 넣고,
보내기 전 privacy.outbound_prompt로 개인정보를 가리고, 출력에 system 줄이 그대로 섞이면 PromptLeakError(422).
"""
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field

from app.core.messages import PROMPT_LEAK_MESSAGE
from app.harness.errors import PromptLeakError
from app.harness.privacy import outbound_prompt
from app.harness.untrusted import block, inline, leaked_lines, output_texts
from app.inventory.models import Item, PolicySuggestion, ReorderPolicy
from app.providers.base import LLMProvider, Prompt, ProviderOutputError

TASK_TYPE = "inventory"
STAGE = "inventory_policy"
_CENT = Decimal("0.01")
_PROMPTS = Path(__file__).parent / "prompts"
_COMMON = Path(__file__).parents[1] / "harness" / "prompts"  # _untrusted.md

_env = Environment(
    loader=ChoiceLoader([FileSystemLoader(_PROMPTS), FileSystemLoader(_COMMON)]),
    undefined=StrictUndefined,
    autoescape=False,
    keep_trailing_newline=False,
)
_env.filters["inline"] = inline
_env.filters["block"] = block


class PolicySuggestionOut(BaseModel):
    """AI 출력 구조(제공자가 response_model로 강제). 수는 float로 받고 코드가 Decimal로 바꾼다."""

    min_stock: float = Field(ge=0, le=1e9, description="최소 재고(품목 단위)")
    target_stock: float = Field(ge=0, le=1e9, description="목표 재고(최소 이상)")
    purchase_unit: float = Field(gt=0, le=1e9, description="한 번에 사는 묶음 단위")
    reason: str = Field(min_length=1, max_length=300, description="추천 이유(근거 숫자 포함, 한두 문장)")


def _tidy(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    out: list[str] = []
    for line in lines:
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out)


def render_prompt(item: Item, policy: ReorderPolicy, on_hand_qty: Decimal | None, usage: Decimal | None) -> Prompt:
    """[순수] 추천 프롬프트. system은 품목과 상관없이 같다."""
    template = _env.get_template("policy_suggestion.md")
    context = template.new_context({"item": item, "policy": policy, "on_hand": on_hand_qty, "usage": usage})
    system = "".join(template.blocks["system"](context))
    user = "".join(template.blocks["user"](context))
    return Prompt(system=_tidy(system), user=_tidy(user))


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def suggest(llm: LLMProvider, prompt: Prompt) -> PolicySuggestion:
    """가린 프롬프트를 보내고 출력을 검증해 추천으로 바꾼다. 제공자 오류는 그대로 올라간다(502·503)."""
    outbound, _ = outbound_prompt(prompt)
    response = llm.complete(task_type=TASK_TYPE, stage=STAGE, prompt=outbound, response_model=PolicySuggestionOut)
    out = response.parsed
    if not isinstance(out, PolicySuggestionOut):
        raise ProviderOutputError("추천 응답이 구조를 따르지 않았습니다.")
    if leaked_lines(outbound.system, output_texts(out)):
        raise PromptLeakError(PROMPT_LEAK_MESSAGE)
    if out.target_stock < out.min_stock:
        raise ProviderOutputError("추천 목표 재고가 최소 재고보다 작습니다.")
    return PolicySuggestion(
        min_stock=_decimal(out.min_stock),
        target_stock=_decimal(out.target_stock),
        purchase_unit=max(_decimal(out.purchase_unit), _CENT),
        reason=out.reason.strip(),
    )
