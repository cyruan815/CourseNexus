from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlashcardParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_count: int = Field(default=20, ge=1, le=100)
    card_style: Literal["term_definition", "question_answer", "mixed"] = "mixed"
    include_formulas: bool = True
    focus: str | None = Field(default=None, min_length=1, max_length=200)


class FlashcardCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: str = Field(min_length=1, max_length=300)
    back: str = Field(min_length=1, max_length=1200)
    tags: list[str] = Field(default_factory=list, max_length=5)
    source_chunk_ids: list[str] = Field(min_length=1)

    @field_validator("front", "back")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Flashcard text cannot be blank")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw in value:
            tag = raw.strip()
            if not tag or len(tag) > 40:
                raise ValueError("Flashcard tags must contain 1..40 characters")
            key = tag.casefold()
            if key not in seen:
                seen.add(key)
                result.append(tag)
        if len(result) > 5:
            raise ValueError("Flashcard supports at most five tags")
        return result


class FlashcardMapResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[FlashcardCandidate] = Field(default_factory=list)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class FlashcardRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^card_\d{3}$")
    front: str = Field(min_length=1, max_length=300)
    back: str = Field(min_length=1, max_length=1200)
    tags: list[str] = Field(default_factory=list, max_length=5)
    mastery_status: Literal["unknown"] = "unknown"
    source_citation_ids: list[str] = Field(default_factory=list)
    sort_order: int = Field(ge=1)


class FlashcardContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cards: list[FlashcardRead] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cards(self) -> "FlashcardContent":
        if [card.id for card in self.cards] != [f"card_{index:03d}" for index in range(1, len(self.cards) + 1)]:
            raise ValueError("Flashcard IDs must be continuous")
        if [card.sort_order for card in self.cards] != list(range(1, len(self.cards) + 1)):
            raise ValueError("Flashcard sort order must be continuous")
        fronts = [" ".join(card.front.split()).casefold() for card in self.cards]
        if len(fronts) != len(set(fronts)):
            raise ValueError("Flashcard fronts must be unique")
        return self
