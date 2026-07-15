from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.modules.generation.generators.flashcard.schemas import FlashcardDraft


class GeneratedContentCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    material_id: str | None
    chunk_id: str | None
    material_name: str
    page: str | None
    page_index: int | None
    hit_text: str
    sort_order: int | None


class GeneratedContentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    study_subtask_id: str | None
    source_message_id: str | None
    content_type: str
    title: str
    content: str | None
    content_json: dict | list | None
    generation_status: str
    material_scope_json: dict | list | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    source_citations: list[GeneratedContentCitationRead] = Field(default_factory=list)


class GeneratedContentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("生成内容名称不能为空")
        return normalized


class FlashcardCardsUpdate(BaseModel):
    cards: list[FlashcardDraft] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_fronts(self) -> "FlashcardCardsUpdate":
        normalized = [" ".join(card.front.split()).casefold() for card in self.cards]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Flashcard fronts must be unique")
        return self


class KnowledgeItemLearningStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learned: bool
