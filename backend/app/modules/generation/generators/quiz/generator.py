from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.quiz.prompts import build_quiz_prompt
from app.modules.generation.generators.quiz.schemas import (
    QuizContent,
    QuizGenerationResult,
    QuizParameters,
    QuizQuestion,
)
from app.modules.generation.generators.topic import contains_chinese, ensure_chinese_topic
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialGenerationContext


def _result_uses_chinese(result: QuizGenerationResult) -> bool:
    return contains_chinese(result.topic_title) and all(
        contains_chinese(question.question_text) for question in result.questions
    )


class QuizGenerator:
    content_type = "quiz"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = QuizParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid quiz parameters", status_code=422) from exc
        prompt = build_quiz_prompt(context, parameters=params)
        result = self.model_provider.generate_structured(
            prompt=prompt,
            output_schema=QuizGenerationResult,
        )
        if not _result_uses_chinese(result):
            result = self.model_provider.generate_structured(
                prompt=(
                    prompt
                    + "\n\nRegenerate the entire quiz because the previous output used English. "
                    "The topic_title and every question must contain Simplified Chinese. Keep formulas, units, "
                    "protocol names, and necessary professional abbreviations unchanged when appropriate."
                ),
                output_schema=QuizGenerationResult,
            )
        if not _result_uses_chinese(result):
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="Quiz questions must be Chinese",
            )
        topic_title = ensure_chinese_topic(result.topic_title)
        questions = [
            QuizQuestion(id=f"q_{index:03d}", sort_order=index, **draft.model_dump())
            for index, draft in enumerate(result.questions[: params.question_count], start=1)
        ]
        try:
            content = QuizContent(questions=questions)
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Quiz structure is invalid") from exc
        return GeneratorOutput(
            title=topic_title,
            content_json=content.model_dump(mode="json", exclude_none=True),
        )


def build_generator(model_provider: ModelProvider) -> QuizGenerator:
    return QuizGenerator(model_provider=model_provider)
