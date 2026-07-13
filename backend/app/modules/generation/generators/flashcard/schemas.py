from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FlashcardParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    card_count: int = Field(default=20, ge=1, le=100)
    card_style: Literal["term_definition", "question_answer", "mixed"] = "mixed"
    include_formulas: bool = True
    focus: str | None = Field(default=None, min_length=1, max_length=200)


class FlashcardDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    front: str = Field(min_length=1, max_length=300)
    back: str = Field(min_length=1, max_length=1200)
    tags: list[str] = Field(default_factory=list, max_length=5)
    explanation: str | None = Field(default=None, min_length=1, max_length=800)

    @field_validator("front", "back")
    @classmethod
    def trim_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Flashcard text cannot be blank")
        return result

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
        return result

    @field_validator("explanation")
    @classmethod
    def trim_explanation(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class FlashcardGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[FlashcardDraft] = Field(min_length=1)


class FlashcardRead(FlashcardDraft):
    id: str = Field(pattern=r"^card_\d{3}$")
    mastery_status: Literal["unknown"] = "unknown"
    sort_order: int = Field(ge=1)


class FlashcardContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[FlashcardRead] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cards(self) -> "FlashcardContent":
        if [item.id for item in self.cards] != [f"card_{i:03d}" for i in range(1, len(self.cards) + 1)]:
            raise ValueError("Flashcard IDs must be continuous")
        if [item.sort_order for item in self.cards] != list(range(1, len(self.cards) + 1)):
            raise ValueError("Flashcard order must be continuous")
        fronts = [" ".join(item.front.split()).casefold() for item in self.cards]
        if len(fronts) != len(set(fronts)):
            raise ValueError("Flashcard fronts must be unique")
        return self
