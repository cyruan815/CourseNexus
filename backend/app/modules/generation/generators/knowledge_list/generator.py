from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.knowledge_list.prompts import build_knowledge_prompt
from app.modules.generation.generators.knowledge_list.schemas import (
    KnowledgeGenerationResult,
    KnowledgeItem,
    KnowledgeListContent,
    KnowledgeListParameters,
)
from app.modules.generation.generators.topic import ensure_chinese_topic
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


IMPORTANCE = {"low": 0, "medium": 1, "high": 2}


class KnowledgeListGenerator:
    content_type = "knowledge_list"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = KnowledgeListParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid knowledge-list parameters", status_code=422) from exc
        result = self.model_provider.generate_structured(
            prompt=build_knowledge_prompt(context, parameters=params),
            output_schema=KnowledgeGenerationResult,
        )
        topic_title = ensure_chinese_topic(result.topic_title)
        minimum = IMPORTANCE[params.minimum_importance]
        drafts = [item for item in result.items if IMPORTANCE[item.importance] >= minimum][: params.item_count]
        items = [
            KnowledgeItem(id=f"kp_{index:03d}", sort_order=index, **draft.model_dump())
            for index, draft in enumerate(drafts, start=1)
        ]
        try:
            content = KnowledgeListContent(items=items)
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Knowledge-list structure is invalid") from exc
        return GeneratorOutput(
            title=topic_title,
            content_json=content.model_dump(mode="json"),
        )


def build_generator(model_provider: ModelProvider) -> KnowledgeListGenerator:
    return KnowledgeListGenerator(model_provider=model_provider)
