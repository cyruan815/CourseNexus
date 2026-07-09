from __future__ import annotations

from pydantic import BaseModel, Field


class MaterialScope(BaseModel):
    include_all_parsed_materials: bool = True
    folder_ids: list[str] = Field(default_factory=list)
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
