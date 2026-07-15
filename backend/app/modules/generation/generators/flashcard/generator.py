from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.flashcard.prompts import build_flashcard_prompt
from app.modules.generation.generators.flashcard.schemas import (
    FlashcardContent,
    FlashcardGenerationResult,
    FlashcardParameters,
    FlashcardRead,
)
from app.modules.generation.generators.topic import ensure_chinese_topic
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


class FlashcardGenerator:
    content_type = "flashcard"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = FlashcardParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid flashcard parameters", status_code=422) from exc
        result = self.model_provider.generate_structured(
            prompt=build_flashcard_prompt(context, parameters=params),
            output_schema=FlashcardGenerationResult,
        )
        topic_title = ensure_chinese_topic(result.topic_title)
        cards = [
            FlashcardRead(id=f"card_{index:03d}", sort_order=index, **draft.model_dump())
            for index, draft in enumerate(result.cards[: params.card_count], start=1)
        ]
        try:
            content = FlashcardContent(cards=cards)
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Flashcard structure is invalid") from exc
        return GeneratorOutput(
            title=topic_title,
            content_json=content.model_dump(mode="json", exclude_none=True),
        )


def build_generator(model_provider: ModelProvider) -> FlashcardGenerator:
    return FlashcardGenerator(model_provider=model_provider)
