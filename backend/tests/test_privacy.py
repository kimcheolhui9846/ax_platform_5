"""외부로 나가는 프롬프트 거르기: 개인정보 가림(되돌리지 않음), 비공개 값 빼기. 세션 상태는 그대로다."""
import pytest

from app.core.assets import InMemoryAssetStore
from app.core.state import CarriedContext, CarriedItem, InfoItem, InfoSource
from app.harness.privacy import PRIVATE_MARK, masked_state, outbound_prompt, private_names, redact
from app.providers.base import Prompt
from app.providers.image import MockImageProvider
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness


@pytest.mark.parametrize(
    ("text", "masked", "kind"),
    [
        ("주민번호 900101-1234567 입니다", "주민번호 [주민번호] 입니다", "resident"),
        ("9001011234567", "[주민번호]", "resident"),
        ("카드 1234-5678-9012-3456", "카드 [카드번호]", "card"),
        ("카드 1234 5678 9012 3456", "카드 [카드번호]", "card"),
        ("계좌 110-123-456789로", "계좌 [계좌번호]로", "account"),
        ("연락처 010-1234-5678", "연락처 [전화번호]", "phone"),
        ("연락처 01012345678", "연락처 [전화번호]", "phone"),
        ("가게 02-345-6789", "가게 [전화번호]", "phone"),
        ("메일 a.b+c@ex-ample.co.kr 로", "메일 [이메일] 로", "email"),
        ("연락 +82 10-1234-5678", "연락 [전화번호]", "phone"),
        ("연락 +821012345678", "연락 [전화번호]", "phone"),
        ("가게 (02) 345-6789", "가게 [전화번호]", "phone"),
        ("대표 1588-1234", "대표 [전화번호]", "phone"),
        ("주민 900101 1234567", "주민 [주민번호]", "resident"),
        ("주민 900101 - 1234567", "주민 [주민번호]", "resident"),
        ("카드 4111111111111111", "카드 [카드번호]", "card"),
        ("번호 010-1234-5678-9", "번호 [계좌번호]", "account"),
    ],
)
def test_redact_masks_each_kind(text, masked, kind):
    assert redact(text) == (masked, {kind: 1})


@pytest.mark.parametrize("text", ["판매가 18,000원", "2026년 10월 18일", "500개 생산", "원가 8000원 / 개", "버전 1.2.3",
    "2026-10-18", "일시 2026-10-18 09:00", "품번 12-34-56", "SKU 2026-1018-01", "10-20대 고객", "바코드 8801234567890"])
def test_redact_leaves_prices_dates_and_quantities(text):
    assert redact(text) == (text, {})


def test_redact_counts_repeats():
    assert redact("010-1111-2222, 010-3333-4444")[1] == {"phone": 2}


def test_private_names_overrides_win_and_false_removes():
    assert private_names(["a", "b"], {}) == frozenset({"a", "b"})
    assert private_names(["a", "b"], {"b": False, "c": True}) == frozenset({"a", "c"})


def test_masked_state_hides_private_values_but_keeps_the_original(harness):
    state = harness.start("향초")
    field = harness.policy.fields[1].name
    state.facts[field] = InfoItem(value="비밀 값", source=InfoSource.USER_FREE_TEXT)
    state.supplements["material"] = InfoItem(value="비밀 소재", source=InfoSource.USER_SUPPLEMENT)
    state.context = CarriedContext(
        session_id="s", task_type="t", version=1, title="t", summary="s",
        items=[CarriedItem(field=field, value="비밀 값", from_name=field)],
    )

    masked = masked_state(state, frozenset({field, "material"}), None)

    assert masked.facts[field].value == PRIVATE_MARK
    assert masked.supplements["material"].value == PRIVATE_MARK
    assert masked.context.items[0].value == PRIVATE_MARK
    assert state.facts[field].value == "비밀 값"  # 원본은 그대로


def test_outbound_prompt_redacts_both_parts_and_sums_counts():
    prompt, counts = outbound_prompt(Prompt(system="고정 010-1234-5678", user="메일 a@b.co 와 010-9999-8888"))
    assert prompt == Prompt(system="고정 [전화번호]", user="메일 [이메일] 와 [전화번호]")
    assert counts == {"phone": 2, "email": 1}


def test_every_llm_call_sends_and_traces_only_filtered_prompts(harness):
    harness.policy.private_fields = ["material"]
    state = harness.start("향초 연락처 010-1234-5678")
    harness.set_supplements(state, {"material": "아주 비밀스러운 소재"})
    harness.generate(state)

    for entry in state.trace:
        text = f"{entry.input.get('system', '')}\n{entry.input.get('user', '')}"
        if entry.input:
            assert "010-1234-5678" not in text
            assert "아주 비밀스러운 소재" not in text
    generate = next(t for t in state.trace if t.stage == "generate" and t.input)
    assert "[전화번호]" in generate.input["user"] and PRIVATE_MARK in generate.input["user"]
    assert generate.input["redactions"] == {"phone": 2}  # 처음 입력 + 사실로 옮긴 같은 글
    assert state.raw_input == "향초 연락처 010-1234-5678"  # 세션 값은 그대로


def test_image_stage_is_filtered_too():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(), images=MockImageProvider(), assets=InMemoryAssetStore())
    harness.policy.image_generation = True
    state = harness.start("향초 연락처 010-1234-5678")

    harness.generate(state)

    entry = next(t for t in state.trace if t.stage == "image")
    assert "010-1234-5678" not in entry.input["user"]
    assert entry.input["redactions"] == {"phone": 2}


def test_image_prompt_hides_private_supplement_values():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(), images=MockImageProvider(), assets=InMemoryAssetStore())
    harness.policy.image_generation = True
    harness.policy.private_fields = ["material"]
    state = harness.start("향초")
    harness.set_supplements(state, {"material": "아주 비밀스러운 소재"})

    harness.generate(state)

    entry = next(t for t in state.trace if t.stage == "image")
    assert "아주 비밀스러운 소재" not in entry.input["user"]
    assert entry.input["redactions"] == {}


def test_private_raw_input_field_hides_the_request_text(harness):
    harness.policy.private_fields = [harness.policy.raw_input_field]
    state = harness.start("아주 은밀한 요청 글")

    harness.generate(state)

    assert state.raw_input == "아주 은밀한 요청 글"
    for entry in state.trace:
        assert "아주 은밀한 요청 글" not in f"{entry.input.get('system', '')}{entry.input.get('user', '')}"
    assert PRIVATE_MARK in next(t for t in state.trace if t.stage == "generate" and t.input).input["user"]


def test_masked_state_hides_raw_input_only_when_its_field_is_private(harness):
    state = harness.start("요청 글")
    assert masked_state(state, frozenset({"idea"}), "idea").raw_input == PRIVATE_MARK
    assert masked_state(state, frozenset(), "idea").raw_input == "요청 글"
    assert masked_state(state, frozenset({"idea"}), None).raw_input == "요청 글"


def test_failure_and_validation_traces_are_redacted():
    from app.core.results import ValidationIssue, ValidationReport
    from app.harness.base import BaseHarness, _validation_trace

    entry = _validation_trace(ValidationReport(issues=[ValidationIssue(rule="r", message="연락처 010-1234-5678 확인")]))
    assert "010-1234-5678" not in str(entry.output)

    state = harness_state()
    BaseHarness._fail_generation(state, ValueError("실패 010-1234-5678"))
    assert "010-1234-5678" not in str(state.trace[-1].output)


def harness_state():
    return SampleHarness(SAMPLE_TASK_DIR, MockProvider()).start("향초")
