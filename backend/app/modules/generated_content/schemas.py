from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
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


class FlashcardCardsUpdate(BaseModel):
    cards: list[FlashcardDraft] = Field(min_length=1)
