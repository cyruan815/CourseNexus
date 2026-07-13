import pytest
from pydantic import ValidationError

from app.modules.generation.generators.flashcard.schemas import FlashcardDraft, FlashcardParameters


def test_flashcard_parameters_keep_poc_preferences() -> None:
    params = FlashcardParameters(card_count=5, card_style="question_answer", include_formulas=False)
    assert params.card_count == 5
    assert params.card_style == "question_answer"
    assert params.include_formulas is False


def test_flashcard_trims_text_and_deduplicates_tags() -> None:
    card = FlashcardDraft(front=" Term ", back=" Definition ", tags=["OS", "os"])
    assert card.front == "Term"
    assert card.tags == ["OS"]
    with pytest.raises(ValidationError):
        FlashcardDraft(front="   ", back="Definition")
