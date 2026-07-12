from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.courses.terms import CourseTerm


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=50)
    teacher: str | None = Field(default=None, max_length=10)
    term: CourseTerm | None = None


class CourseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=50)
    teacher: str | None = Field(default=None, max_length=10)
    term: CourseTerm | None = None


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


class CourseTermOptionRead(BaseModel):
    value: CourseTerm
    label: str
