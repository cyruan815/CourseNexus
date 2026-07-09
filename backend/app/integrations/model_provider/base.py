from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.material_context.schemas import ContextChunk


@dataclass(frozen=True)
class ModelAnswer:
    answer_text: str
    citation_chunk_ids: list[str]


class ModelProvider(Protocol):
    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        """Answer a course question based on resolved material context."""
