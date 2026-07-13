from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MaterialScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_all_parsed_materials: bool = True
    material_ids: list[str] = Field(default_factory=list)


class ContextChunk(BaseModel):
    material_id: str
    chunk_id: str
    chunk_index: int = 0
    material_name: str
    page: str | None
    page_index: int | None
    heading: str | None
    content_text: str
    score: float | None = None


class MaterialContextResult(BaseModel):
    chunks: list[ContextChunk]
    no_parsed_material: bool


class MaterialContextBatch(BaseModel):
    chunks: list[ContextChunk]
    material_ids: list[str]
    estimated_tokens: int


class MaterialQualityWarning(BaseModel):
    code: str
    message: str
    material_id: str
    material_name: str
    parse_quality: str
    page_no: int | None = None
    component: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class MaterialQualitySummary(BaseModel):
    warnings: list[MaterialQualityWarning] = Field(default_factory=list)


class MaterialGenerationContext(BaseModel):
    chunks: list[ContextChunk]
    material_ids: list[str]
    text: str
    estimated_tokens: int
