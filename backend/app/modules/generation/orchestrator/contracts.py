from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.modules.material_context.schemas import MaterialContextResult, MaterialScope


class GenerateContentRequest(BaseModel):
    content_type: str = Field(min_length=1, max_length=32)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    parameters: dict[str, Any] = Field(default_factory=dict)


class GeneratorOutput(BaseModel):
    title: str
    content: str | None = None
    content_json: dict | list | None = None
    citation_chunk_ids: list[str] = Field(default_factory=list)


class Generator(Protocol):
    def generate(self, *, context: MaterialContextResult, parameters: dict[str, Any]) -> GeneratorOutput:
        """Generate structured content from resolved material context."""
