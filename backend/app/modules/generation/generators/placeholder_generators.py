from __future__ import annotations

from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextResult


class PlaceholderGenerator:
    def __init__(self, *, content_type: str) -> None:
        self.content_type = content_type

    def generate(self, *, context: MaterialContextResult, parameters: dict[str, object]) -> GeneratorOutput:
        first_chunk = context.chunks[0]
        title = self.content_type.replace("_", " ").title()
        return GeneratorOutput(
            title=title,
            content=first_chunk.content_text,
            content_json=self._content_json(first_chunk.content_text),
            citation_chunk_ids=[first_chunk.chunk_id],
        )

    def _content_json(self, content_text: str) -> dict[str, object]:
        if self.content_type == "outline":
            return {"items": [content_text]}
        if self.content_type == "flashcard":
            return {"cards": [{"front": "Key point", "back": content_text}]}
        if self.content_type == "quiz":
            return {"questions": [{"prompt": "Review this material", "answer": content_text}]}
        if self.content_type == "mindmap":
            return {"nodes": [{"id": "root", "label": content_text}], "edges": []}
        if self.content_type == "knowledge_list":
            return {"knowledge_points": [content_text]}
        return {"content": content_text}
