from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    teacher: str | None = Field(default=None, max_length=255)
    term: str | None = Field(default=None, max_length=255)


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    teacher: str | None = Field(default=None, max_length=255)
    term: str | None = Field(default=None, max_length=255)


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: str | None
    teacher: str | None
    term: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
