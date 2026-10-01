from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MaterialFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sort_order: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("目录名称不能为空")
        return normalized


class MaterialFolderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_order: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("目录名称不能为空")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "MaterialFolderUpdate":
        if self.name is None and self.sort_order is None:
            raise ValueError("至少提供一个要修改的字段")
        return self


class MaterialFolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    name: str
    sort_order: int | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MaterialFolderAssignment(BaseModel):
    folder_id: str | None = None


class MaterialUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("资料名称不能为空")
        return normalized


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
    parse_quality: str
    parse_diagnostics_json: dict | list | None
    page_count: int | None
    active_parse_version_id: str | None
    is_learning_ready: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
