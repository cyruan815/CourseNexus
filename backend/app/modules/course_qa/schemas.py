from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.material_context.schemas import MaterialScope


class CourseQuestionCreate(BaseModel):
    conversation_id: str | None = None
    question: str = Field(min_length=1)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    source_page: str | None = Field(default="course_detail", max_length=64)


class SourceCitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    material_id: str | None
    chunk_id: str | None
    material_name: str
    page: str | None
    page_index: int | None
    hit_text: str


class CourseAnswerRead(BaseModel):
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    answer_text: str
    answer_type: str
    source_citations: list[SourceCitationRead]
    used_material_ids: list[str] = Field(default_factory=list)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    title: str | None
    source_page: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    course_id: str
    role: str
    content: str
    answer_type: str | None
    generation_status: str | None
    error_code: str | None
    material_scope_json: dict | list | None
    created_at: datetime
