from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.modules.material_context.schemas import ContextChunk


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


@dataclass(frozen=True)
class ModelAnswer:
    answer_text: str
    citation_chunk_ids: list[str]


class ModelProvider(Protocol):
    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        """Answer a course question based on resolved material context."""

    def generate_structured(
        self,
        *,
        prompt: str,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        """Generate a caller-defined Pydantic structured output."""
