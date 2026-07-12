from __future__ import annotations

import re
from dataclasses import dataclass
from math import ceil
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.flashcard.prompts import build_flashcard_map_prompt
from app.modules.generation.generators.flashcard.schemas import (
    FlashcardCandidate,
    FlashcardContent,
    FlashcardMapResult,
    FlashcardParameters,
    FlashcardRead,
)
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def _looks_like_formula(card: FlashcardCandidate) -> bool:
    return bool(re.search(r"[=+*/^]|\\[a-zA-Z]+", card.front + " " + card.back))


@dataclass
class _MergedCard:
    candidate: FlashcardCandidate
    chunk_ids: list[str]
    material_ids: set[str]
    first_position: int


class FlashcardGenerator:
    content_type = "flashcard"

    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(self, *, batches: tuple[MaterialContextBatch, ...], expected_material_ids: frozenset[str], parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params = FlashcardParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid flashcard parameters", status_code=422) from exc
        budget = min(30, max(3, ceil(params.card_count / len(batches)) + 2))
        return run_material_coverage(
            batches=batches, expected_material_ids=set(expected_material_ids),
            map_batch=lambda batch: self.model_provider.generate_structured(
                prompt=build_flashcard_map_prompt(batch, parameters=params, candidate_budget=budget),
                output_schema=FlashcardMapResult,
            ),
            reduce_results=lambda mapped: self._reduce(mapped, batches=batches, params=params),
        ).value

    def _reduce(self, mapped: list[FlashcardMapResult], *, batches: tuple[MaterialContextBatch, ...], params: FlashcardParameters) -> GeneratorOutput:
        allowed = {chunk.chunk_id for batch in batches for chunk in batch.chunks}
        material_by_chunk = {chunk.chunk_id: chunk.material_id for batch in batches for chunk in batch.chunks}
        merged: dict[str, _MergedCard] = {}
        position = 0
        for result in mapped:
            for candidate in result.candidates:
                chunk_ids = list(dict.fromkeys(item for item in candidate.source_chunk_ids if item in allowed))
                if not chunk_ids:
                    continue
                key = _normalized(candidate.front)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = _MergedCard(candidate, chunk_ids, {material_by_chunk[item] for item in chunk_ids}, position)
                    position += 1
                else:
                    for chunk_id in chunk_ids:
                        if chunk_id not in existing.chunk_ids:
                            existing.chunk_ids.append(chunk_id)
                            existing.material_ids.add(material_by_chunk[chunk_id])
                    tags = existing.candidate.tags + [tag for tag in candidate.tags if tag.casefold() not in {item.casefold() for item in existing.candidate.tags}]
                    existing.candidate.tags = tags[:5]
        if not merged:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Flashcard result is empty")
        focus = _normalized(params.focus) if params.focus else None
        cards = list(merged.values())
        cards.sort(key=lambda item: (
            0 if focus and focus in _normalized(item.candidate.front + " " + item.candidate.back) else 1,
            1 if not params.include_formulas and _looks_like_formula(item.candidate) else 0,
            -len(item.material_ids), item.first_position,
        ))
        cards = cards[: params.card_count]
        final: list[FlashcardRead] = []
        bindings: dict[str, list[str]] = {}
        for index, item in enumerate(cards, start=1):
            card_id = f"card_{index:03d}"
            final.append(FlashcardRead(
                id=card_id, front=item.candidate.front, back=item.candidate.back,
                tags=item.candidate.tags, mastery_status="unknown", source_citation_ids=[], sort_order=index,
            ))
            bindings[card_id] = item.chunk_ids
        content = FlashcardContent(cards=final)
        return GeneratorOutput(
            title=f"记忆卡片（{len(final)}张）", content=None,
            content_json=content.model_dump(mode="json"), item_citation_chunk_ids=bindings,
        )


def build_generator(model_provider: ModelProvider) -> FlashcardGenerator:
    return FlashcardGenerator(model_provider=model_provider)
