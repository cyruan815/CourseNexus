from __future__ import annotations

from app.integrations.model_provider.base import ModelAnswer
from app.modules.material_context.schemas import ContextChunk


class MockModelProvider:
    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        first_chunk = context_chunks[0]
        return ModelAnswer(
            answer_text=f"Mock answer based on: {first_chunk.content_text}",
            citation_chunk_ids=[first_chunk.chunk_id],
        )
