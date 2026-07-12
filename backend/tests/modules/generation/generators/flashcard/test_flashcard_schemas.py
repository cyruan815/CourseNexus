from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.flashcard.schemas import FlashcardCandidate, FlashcardParameters


def test_parameters_use_defaults() -> None:
    params = FlashcardParameters.model_validate({})
    assert (params.card_count, params.card_style, params.include_formulas) == (20, "mixed", True)


@pytest.mark.parametrize("payload", [{"card_count": 0}, {"card_count": 101}, {"card_style": "bad"}, {"unknown": 1}])
def test_parameters_reject_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        FlashcardParameters.model_validate(payload)


def test_candidate_normalizes_and_deduplicates_tags() -> None:
    card = FlashcardCandidate(
        front="What is a process?", back="A program in execution.",
        tags=[" OS ", "os", "process"], source_chunk_ids=["c1"],
    )
    assert card.tags == ["OS", "process"]


def test_candidate_rejects_empty_citations_and_too_many_tags() -> None:
    with pytest.raises(ValidationError):
        FlashcardCandidate(front="Front", back="Back", tags=[], source_chunk_ids=[])
    with pytest.raises(ValidationError):
        FlashcardCandidate(front="Front", back="Back", tags=["1", "2", "3", "4", "5", "6"], source_chunk_ids=["c1"])
