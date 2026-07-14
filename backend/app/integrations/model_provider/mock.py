from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelAnswer, StructuredOutputT
from app.modules.material_context.schemas import ContextChunk


class MockModelProvider:
    def __init__(self, structured_outputs: dict[type[BaseModel], BaseModel | dict] | None = None, text_outputs: list[str] | None = None) -> None:
        self.structured_outputs = structured_outputs or {}
        self.text_outputs = list(text_outputs or [])

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        first_chunk = context_chunks[0]
        return ModelAnswer(
            answer_text=f"Mock answer based on: {first_chunk.content_text} [[cite:{first_chunk.chunk_id}]]",
            citation_chunk_ids=[first_chunk.chunk_id],
        )

    def generate_text(self, *, prompt: str) -> str:
        if self.text_outputs:
            return self.text_outputs.pop(0)
        return "# Mock Markdown\n\nMock generated content."

    def generate_structured(
        self,
        *,
        prompt: str,
        output_schema: type[StructuredOutputT],
    ) -> StructuredOutputT:
        try:
            return output_schema.model_validate(self.structured_outputs.get(output_schema, {}))
        except ValidationError as exc:
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="Mock structured output does not match requested schema",
                status_code=500,
            ) from exc
