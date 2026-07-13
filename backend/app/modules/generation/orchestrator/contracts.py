from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.model_provider.base import ModelProvider
from app.modules.material_context.schemas import MaterialGenerationContext, MaterialScope


class GenerateContentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_type: str = Field(min_length=1, max_length=32)
    material_scope: MaterialScope = Field(default_factory=MaterialScope)
    parameters: dict[str, Any] = Field(default_factory=dict)


class GeneratorOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content: str | None = None
    content_json: dict[str, Any]
    item_citation_chunk_ids: dict[str, list[str]] = Field(default_factory=dict)


class Generator(Protocol):
    content_type: str

    def generate(
        self,
        *,
        context: MaterialGenerationContext,
        parameters: dict[str, Any],
    ) -> GeneratorOutput: ...


GeneratorFactory = Callable[[ModelProvider], Generator]
