from __future__ import annotations

from typing import Any

from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextBatch


class PlaceholderGenerator:
    def __init__(self, *, content_type: str, model_provider: ModelProvider) -> None:
        self.content_type = content_type
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        first_chunk = next(chunk for batch in batches for chunk in batch.chunks)
        content_json, item_id = self._content_json(first_chunk.content_text)
        return GeneratorOutput(
            title=self.content_type.replace("_", " ").title(),
            content=first_chunk.content_text,
            content_json=content_json,
            item_citation_chunk_ids={item_id: [first_chunk.chunk_id]},
        )

    def _content_json(self, content_text: str) -> tuple[dict[str, Any], str]:
        if self.content_type == "outline":
            item_id = "outline-item-1"
            return {
                "items": [
                    {
                        "id": item_id,
                        "text": content_text,
                        "source_citation_ids": [],
                    }
                ]
            }, item_id
        if self.content_type == "flashcard":
            item_id = "flashcard-1"
            return {
                "cards": [
                    {
                        "id": item_id,
                        "front": "Key point",
                        "back": content_text,
                        "source_citation_ids": [],
                    }
                ]
            }, item_id
        if self.content_type == "quiz":
            item_id = "quiz-question-1"
            return {
                "questions": [
                    {
                        "id": item_id,
                        "prompt": "Review this material",
                        "answer": content_text,
                        "source_citation_ids": [],
                    }
                ]
            }, item_id
        if self.content_type == "mindmap":
            item_id = "mindmap-root"
            return {
                "nodes": [
                    {
                        "id": item_id,
                        "label": content_text,
                        "source_citation_ids": [],
                    }
                ],
                "edges": [],
            }, item_id
        if self.content_type == "knowledge_list":
            item_id = "knowledge-point-1"
            return {
                "knowledge_points": [
                    {
                        "id": item_id,
                        "content": content_text,
                        "source_citation_ids": [],
                    }
                ]
            }, item_id

        item_id = f"{self.content_type}-item-1"
        return {
            "items": [
                {
                    "id": item_id,
                    "text": content_text,
                    "source_citation_ids": [],
                }
            ]
        }, item_id
