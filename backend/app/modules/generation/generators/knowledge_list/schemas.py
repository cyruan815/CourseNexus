from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Importance = Literal["low", "medium", "high"]


class KnowledgeListParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_count: int = Field(default=50, ge=1, le=200)
    extraction_focus: Literal["balanced", "definitions", "formulas", "pitfalls"] = "balanced"
    minimum_importance: Importance = "low"
    focus: str | None = Field(default=None, min_length=1, max_length=200)


class KnowledgeDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    definition: str = Field(min_length=1, max_length=1200)
    importance: Importance
    related_section: str = Field(min_length=1, max_length=200)

    @field_validator("name", "definition", "related_section")
    @classmethod
    def trim_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Knowledge item fields cannot be blank")
        return result


class KnowledgeGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[KnowledgeDraft] = Field(min_length=1)


class KnowledgeItem(KnowledgeDraft):
    id: str = Field(pattern=r"^kp_\d{3}$")
    sort_order: int = Field(ge=1)


class KnowledgeListContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[KnowledgeItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> "KnowledgeListContent":
        if [item.id for item in self.items] != [f"kp_{i:03d}" for i in range(1, len(self.items) + 1)]:
            raise ValueError("Knowledge IDs must be continuous")
        if [item.sort_order for item in self.items] != list(range(1, len(self.items) + 1)):
            raise ValueError("Knowledge order must be continuous")
        names = [" ".join(item.name.split()).casefold() for item in self.items]
        if len(names) != len(set(names)):
            raise ValueError("Knowledge names must be unique")
        return self
