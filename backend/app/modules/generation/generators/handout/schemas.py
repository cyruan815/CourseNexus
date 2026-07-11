from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HandoutGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = "zh-CN"
    detail_level: Literal["brief", "standard", "deep"] = "standard"


class HandoutSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    key_points: list[str] = Field(min_length=1)
    source_citation_ids: list[str] = Field(min_length=1)
    sort_order: int = Field(ge=1)

    @field_validator("key_points", "source_citation_ids")
    @classmethod
    def _non_empty_strings(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("items must be non-empty strings")
        return value


class HandoutContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overview: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    sections: list[HandoutSection] = Field(min_length=1)
    summary: str = Field(min_length=1)

    @field_validator("learning_objectives")
    @classmethod
    def _objectives_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("learning objectives must be non-empty")
        return value
