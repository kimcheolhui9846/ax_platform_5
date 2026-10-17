"""결과 섹션: LLM이 쓴 카드를 순서대로 섹션(글 블록 하나)으로 바꾸고, 옛 결과(cards)도 섹션으로 읽는다."""
from app.core.results import (
    CardType,
    GenerationResult,
    ResultCard,
    ResultSection,
    TextBlock,
    compose_full_text,
    section_text,
    sections_from_cards,
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
