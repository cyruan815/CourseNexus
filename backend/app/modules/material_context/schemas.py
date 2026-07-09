from __future__ import annotations

from pydantic import BaseModel, Field


class MaterialScope(BaseModel):
    include_all_parsed_materials: bool = True
    folder_ids: list[str] = Field(default_factory=list)
    material_ids: list[str] = Field(default_factory=list)


class ContextChunk(BaseModel):
    material_id: str
    chunk_id: str
    material_name: str
    page: str | None
    page_index: int | None
    heading: str | None
    content_text: str


class MaterialContextResult(BaseModel):
    chunks: list[ContextChunk]
    no_parsed_material: bool
