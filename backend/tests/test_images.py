"""결과 이미지: policy.image_generation을 켠 과제만 대표 섹션에 이미지 한 장(Mock SVG). 실패해도 결과는 살린다."""
from app.core.assets import InMemoryAssetStore
from app.core.messages import IMAGE_FAILED_MESSAGE
from app.core.results import CardType, ImageBlock, ResultSection, TextBlock, image_target, section_text
from app.main import create_app
from app.providers.image import PLACEHOLDER_SVG, MockImageProvider
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness, api_client


def make_harness(images: MockImageProvider, assets: InMemoryAssetStore, on: bool = True) -> SampleHarness:
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(), images=images, assets=assets)
    harness.policy.image_generation = on
    return harness


def section(order: int, kind: CardType) -> ResultSection:
    return ResultSection(order=order, heading=f"h{order}", kind=kind, blocks=[TextBlock(text="t")])


def test_image_target_prefers_the_first_suggestion():
    assert image_target([section(1, CardType.DIAGNOSIS), section(2, CardType.SUGGESTION), section(3, CardType.SUGGESTION)]).order == 2
    assert image_target([section(1, CardType.DIAGNOSIS), section(2, CardType.ACTION)]).order == 1
    assert image_target([]) is None


def test_generate_adds_one_image_block_stored_for_the_owner():
    images, assets = MockImageProvider(), InMemoryAssetStore()
    harness = make_harness(images, assets)
    state = harness.start("향초", owner_id="owner-0001")

    harness.generate(state)

    blocks = [(s.order, b) for s in state.result.sections for b in s.blocks if b.type == "image"]
    assert len(blocks) == 1
    order, block = blocks[0]
    assert order == image_target(state.result.sections).order
    assert isinstance(block, ImageBlock) and block.origin == "ai_generated"
    stored = assets.get(block.asset_id)
    assert (stored.owner_id, stored.mime, stored.data) == ("owner-0001", "image/svg+xml", PLACEHOLDER_SVG)
    assert images.calls == ["sample_task"]
    entry = next(t for t in state.trace if t.stage == "image")
    assert entry.output == {"asset_id": block.asset_id, "mime": "image/svg+xml", "bytes": len(PLACEHOLDER_SVG)}
    assert (entry.provider, entry.model) == ("mock", "mock-image")
    assert block.asset_id not in state.result.full_text  # 완성본 글에는 이미지가 없다


def test_image_prompt_keeps_session_values_out_of_the_system_part():
    harness = make_harness(MockImageProvider(), InMemoryAssetStore())
    state = harness.start("아주 특별한 향초")
    harness.generate(state)
    entry = next(t for t in state.trace if t.stage == "image")
    target = image_target(state.result.sections)
    assert "아주 특별한 향초" in entry.input["user"] and "아주 특별한 향초" not in entry.input["system"]
    assert target.heading in entry.input["user"]


def test_tasks_without_image_generation_make_no_image():
    images = MockImageProvider()
    harness = make_harness(images, InMemoryAssetStore(), on=False)
    state = harness.start("향초")
    harness.generate(state)
    assert images.calls == []
    assert all(b.type == "text" for s in state.result.sections for b in s.blocks)


def test_image_failure_keeps_the_result_with_a_warning():
    harness = make_harness(MockImageProvider(fail=True), InMemoryAssetStore())
    state = harness.start("향초")

    harness.generate(state)

    assert state.status.value == "completed"
    assert all(b.type == "text" for s in state.result.sections for b in s.blocks)
    assert [(i.rule, i.message) for i in state.validation.issues if i.rule == "image_unavailable"] == [
        ("image_unavailable", IMAGE_FAILED_MESSAGE)
    ]
    assert next(t for t in state.trace if t.stage == "image").output["error"]


def test_editing_text_keeps_the_generated_image():
    harness = make_harness(MockImageProvider(), InMemoryAssetStore())
    state = harness.start("향초")
    harness.generate(state)
    target = image_target(state.result.sections)

    harness.edit_section(state, target.order, "고친 글")

    edited = next(s for s in state.result.sections if s.order == target.order)
    assert section_text(edited) == "고친 글"
    assert [b.type for b in edited.blocks] == ["text", "image"]


def test_branding_and_marketing_turn_images_on_by_default():
    app = create_app(provider=MockProvider())
    policies = {h.task_type: h.policy.image_generation for h in app.state.registry.all()}
    assert policies == {"business_plan": False, "product_planning": False, "branding": True, "marketing_content": True}


def test_generated_image_is_served_through_the_api():
    assets = InMemoryAssetStore()
    client = api_client(create_app(provider=MockProvider(), images=MockImageProvider(), assets=assets))
    sid = client.post("/api/v1/coaching/tasks/branding/sessions", json={"raw_input": "한글 파우치 브랜드"}).json()["session_id"]

    result = client.post(f"/api/v1/coaching/sessions/{sid}/generate").json()

    [block] = [b for s in result["result"]["sections"] for b in s["blocks"] if b["type"] == "image"]
    assert set(block) == {"type", "asset_id", "alt", "caption", "origin"}
    assert client.get(f"/api/v1/coaching/assets/{block['asset_id']}").content == PLACEHOLDER_SVG
