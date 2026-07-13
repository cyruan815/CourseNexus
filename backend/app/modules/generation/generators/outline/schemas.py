from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OutlineParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization: Literal["source_order", "topic", "review_path"] = "review_path"
    section_count: int = Field(default=12, ge=1, le=30)
    review_goal: str | None = Field(default=None, min_length=1, max_length=300)
    detail_level: Literal["concise", "standard", "detailed"] = "standard"


class OutlineDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2000)
    review_suggestion: str = Field(min_length=1, max_length=800)

    @field_validator("title", "summary", "review_suggestion")
    @classmethod
    def trim_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Outline text cannot be blank")
        return result


class OutlineGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[OutlineDraft] = Field(min_length=1)


class OutlineSection(OutlineDraft):
    id: str = Field(pattern=r"^sec_\d{3}$")
    sort_order: int = Field(ge=1)


class OutlineContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sections: list[OutlineSection] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sections(self) -> "OutlineContent":
        if [item.id for item in self.sections] != [f"sec_{i:03d}" for i in range(1, len(self.sections) + 1)]:
            raise ValueError("Outline IDs must be continuous")
        if [item.sort_order for item in self.sections] != list(range(1, len(self.sections) + 1)):
            raise ValueError("Outline order must be continuous")
        titles = [" ".join(item.title.split()).casefold() for item in self.sections]
        if len(titles) != len(set(titles)):
            raise ValueError("Outline titles must be unique")
        return self
