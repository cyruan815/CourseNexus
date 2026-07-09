from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialLinkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_url: str = Field(min_length=1, max_length=2048)


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    user_id: str
    folder_id: str | None
    name: str
    material_type: str
    source_type: str
    file_url: str | None
    source_url: str | None
    file_size: int | None
    mime_type: str | None
    parse_status: str
    parse_error: str | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
