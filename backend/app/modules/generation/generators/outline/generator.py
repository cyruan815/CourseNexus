from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.outline.prompts import build_outline_prompt
from app.modules.generation.generators.outline.schemas import (
    OutlineContent,
    OutlineGenerationResult,
    OutlineParameters,
    OutlineSection,
)
from app.modules.generation.generators.topic import ensure_chinese_topic
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


class OutlineGenerator:
    content_type = "outline"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = OutlineParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid outline parameters", status_code=422) from exc
        result = self.model_provider.generate_structured(
            prompt=build_outline_prompt(context, parameters=params),
            output_schema=OutlineGenerationResult,
        )
        topic_title = ensure_chinese_topic(result.topic_title)
        summary_limit = {"concise": 300, "standard": 800, "detailed": 2000}[params.detail_level]
        sections = [
            OutlineSection(
                id=f"sec_{index:03d}",
                title=f"{index}. {draft.title}",
                summary=draft.summary[:summary_limit],
                review_suggestion=draft.review_suggestion,
                sort_order=index,
            )
            for index, draft in enumerate(result.sections[: params.section_count], start=1)
        ]
        try:
            content = OutlineContent(sections=sections)
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Outline structure is invalid") from exc
        return GeneratorOutput(
            title=topic_title,
            content_json=content.model_dump(mode="json"),
        )


def build_generator(model_provider: ModelProvider) -> OutlineGenerator:
    return OutlineGenerator(model_provider=model_provider)
