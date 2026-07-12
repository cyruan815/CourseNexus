from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.quiz.prompts import build_quiz_map_prompt
from app.modules.generation.generators.quiz.schemas import (
    QuizCandidate,
    QuizContent,
    QuizMapResult,
    QuizParameters,
    QuizQuestion,
)
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass
class _MergedCandidate:
    candidate: QuizCandidate
    chunk_ids: list[str]
    material_ids: set[str]
    first_position: int


class QuizGenerator:
    content_type = "quiz"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        try:
            params = QuizParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid quiz parameters", status_code=422) from exc
        candidate_budget = min(20, max(2, ceil(params.question_count / len(batches)) + 1))
        return run_material_coverage(
            batches=batches,
            expected_material_ids=set(expected_material_ids),
            map_batch=lambda batch: self.model_provider.generate_structured(
                prompt=build_quiz_map_prompt(batch, parameters=params, candidate_budget=candidate_budget),
                output_schema=QuizMapResult,
            ),
            reduce_results=lambda mapped: self._reduce(mapped, batches=batches, params=params),
        ).value

    def _reduce(
        self,
        mapped: list[QuizMapResult],
        *,
        batches: tuple[MaterialContextBatch, ...],
        params: QuizParameters,
    ) -> GeneratorOutput:
        allowed = {chunk.chunk_id for batch in batches for chunk in batch.chunks}
        material_by_chunk = {chunk.chunk_id: chunk.material_id for batch in batches for chunk in batch.chunks}
        merged: dict[str, _MergedCandidate] = {}
        position = 0
        for result in mapped:
            for candidate in result.candidates:
                if candidate.question_type not in params.question_types:
                    continue
                if params.difficulty != "mixed" and candidate.difficulty != params.difficulty:
                    continue
                chunk_ids = list(dict.fromkeys(chunk_id for chunk_id in candidate.source_chunk_ids if chunk_id in allowed))
                if not chunk_ids:
                    continue
                key = _normalized(candidate.question_text)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = _MergedCandidate(
                        candidate=candidate,
                        chunk_ids=chunk_ids,
                        material_ids={material_by_chunk[item] for item in chunk_ids},
                        first_position=position,
                    )
                    position += 1
                else:
                    for chunk_id in chunk_ids:
                        if chunk_id not in existing.chunk_ids:
                            existing.chunk_ids.append(chunk_id)
                            existing.material_ids.add(material_by_chunk[chunk_id])
        if not merged:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Quiz contains no legal questions")

        focus = _normalized(params.focus) if params.focus else None
        buckets: dict[str, list[_MergedCandidate]] = {item: [] for item in params.question_types}
        for item in merged.values():
            buckets[item.candidate.question_type].append(item)
        for bucket in buckets.values():
            bucket.sort(
                key=lambda item: (
                    0 if focus and focus in _normalized(item.candidate.question_text + " " + item.candidate.explanation) else 1,
                    -len(item.material_ids),
                    item.first_position,
                )
            )

        selected: list[_MergedCandidate] = []
        while len(selected) < params.question_count:
            added = False
            for question_type in params.question_types:
                if buckets[question_type] and len(selected) < params.question_count:
                    selected.append(buckets[question_type].pop(0))
                    added = True
            if not added:
                break

        questions: list[QuizQuestion] = []
        bindings: dict[str, list[str]] = {}
        for index, item in enumerate(selected, start=1):
            question_id = f"q_{index:03d}"
            payload = item.candidate.model_dump(exclude={"source_chunk_ids"})
            questions.append(
                QuizQuestion(id=question_id, sort_order=index, source_citation_ids=[], **payload)
            )
            bindings[question_id] = item.chunk_ids
        try:
            content = QuizContent(questions=questions)
        except ValidationError as exc:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Quiz structure is invalid") from exc
        return GeneratorOutput(
            title=f"课程自测（{len(questions)}题）",
            content=None,
            content_json=content.model_dump(mode="json"),
            item_citation_chunk_ids=bindings,
        )


def build_generator(model_provider: ModelProvider) -> QuizGenerator:
    return QuizGenerator(model_provider=model_provider)
