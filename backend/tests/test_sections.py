"""결과 섹션: LLM이 쓴 카드를 순서대로 섹션(글 블록 하나)으로 바꾸고, 옛 결과(cards)도 섹션으로 읽는다."""
from app.core.results import (
    CardType,
    GenerationResult,
    ImageBlock,
    ImageOrigin,
    ResultCard,
    ResultSection,
    TextBlock,
    compose_full_text,
    section_text,
    sections_from_cards,
    with_section_text,
)


def card(order: int, title: str, body: str, kind: CardType = CardType.DIAGNOSIS) -> ResultCard:
    return ResultCard(card_type=kind, title=title, body=body, order=order)


def test_cards_become_ordered_sections_with_one_text_block():
    sections = sections_from_cards([card(2, "실행", "다섯 명에게 묻기", CardType.ACTION), card(1, "콘셉트", "한글 파우치")])

    assert [(s.order, s.heading, s.kind) for s in sections] == [(1, "콘셉트", CardType.DIAGNOSIS), (2, "실행", CardType.ACTION)]
    assert sections[0].blocks == [TextBlock(text="한글 파우치")]


def test_section_and_full_text():
    sections = [
        ResultSection(order=1, heading="콘셉트", kind=CardType.DIAGNOSIS, blocks=[TextBlock(text="가"), TextBlock(text="나")]),
        ResultSection(order=2, heading="실행", kind=CardType.ACTION, blocks=[TextBlock(text="다")]),
    ]
    assert section_text(sections[0]) == "가\n\n나"
    assert compose_full_text(sections) == "콘셉트\n가\n\n나\n\n실행\n다"


def test_results_saved_with_cards_are_read_as_sections():
    legacy = {
        "cards": [{"card_type": "diagnosis", "title": "콘셉트", "body": "한글 파우치", "order": 1}],
        "assumptions": [],
        "full_text": "콘셉트\n한글 파우치",
        "content": {},
        "generated_at": "2026-10-16T09:00:00Z",
    }

    result = GenerationResult.model_validate(legacy)

    assert [(s.heading, section_text(s)) for s in result.sections] == [("콘셉트", "한글 파우치")]


def test_legacy_cards_longer_than_the_new_limit_still_load():
    """길이 상한(2500)은 LLM 출력 제약이다. 상한이 생기기 전에 저장한 결과는 그대로 읽는다."""
    long_body = "가" * 3000
    legacy = {
        "cards": [{"card_type": "diagnosis", "title": "콘셉트", "body": long_body, "order": 1}],
        "full_text": long_body,
        "content": {},
    }

    result = GenerationResult.model_validate(legacy)

    assert section_text(result.sections[0]) == long_body


def test_section_orders_are_renumbered_even_when_cards_repeat_an_order():
    overlapped = sections_from_cards([card(1, "가", "a"), card(1, "나", "b"), card(2, "다", "c")])
    assert [(s.order, s.heading) for s in overlapped] == [(1, "가"), (2, "나"), (3, "다")]

    all_same = sections_from_cards([card(1, "가", "a"), card(1, "나", "b"), card(1, "다", "c")])
    assert [(s.order, s.heading) for s in all_same] == [(1, "가"), (2, "나"), (3, "다")]


def test_card_body_is_bounded_by_the_edit_limit():
    from app.schemas.coaching import EditSectionRequest

    body_max = next(m.max_length for m in ResultCard.model_fields["body"].metadata if hasattr(m, "max_length"))
    edit_max = next(m.max_length for m in EditSectionRequest.model_fields["text"].metadata if hasattr(m, "max_length"))
    assert body_max <= edit_max


def image(asset_id: str = "asset_" + "0" * 32) -> ImageBlock:
    return ImageBlock(asset_id=asset_id, alt="향초 참고 이미지", caption="AI 참고 이미지", origin=ImageOrigin.AI_GENERATED)


def result_with(blocks) -> GenerationResult:
    section = ResultSection(order=1, heading="콘셉트", kind="diagnosis", blocks=blocks)
    return GenerationResult(sections=[section], full_text="", content={})


def test_section_blocks_tell_text_and_image_apart_by_type():
    loaded = GenerationResult.model_validate(
        result_with([TextBlock(text="글"), image()]).model_dump(mode="json")
    )
    assert [b.type for b in loaded.sections[0].blocks] == ["text", "image"]
    assert isinstance(loaded.sections[0].blocks[1], ImageBlock)
    assert section_text(loaded.sections[0]) == "글"  # 이미지는 본문 글이 아니다


def test_editing_text_keeps_image_blocks_in_place():
    original = result_with([TextBlock(text="앞 글"), image(), TextBlock(text="뒤 글")])

    edited = with_section_text(original, 1, "새 글")

    assert [b.type for b in edited.sections[0].blocks] == ["text", "image"]
    assert edited.sections[0].blocks[0].text == "새 글"
    assert edited.sections[0].blocks[1] == original.sections[0].blocks[1]


def test_editing_a_section_with_only_an_image_puts_the_text_first():
    edited = with_section_text(result_with([image()]), 1, "새 글")
    assert [b.type for b in edited.sections[0].blocks] == ["text", "image"]
