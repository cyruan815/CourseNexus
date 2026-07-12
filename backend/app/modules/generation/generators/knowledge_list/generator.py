from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.knowledge_list.prompts import build_knowledge_map_prompt
from app.modules.generation.generators.knowledge_list.schemas import (
    KnowledgeCandidate,
    KnowledgeItem,
    KnowledgeListContent,
    KnowledgeListParameters,
    KnowledgeMapResult,
)
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch


IMPORTANCE = {"low": 0, "medium": 1, "high": 2}


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass
class _MergedItem:
    candidate: KnowledgeCandidate
    chunk_ids: list[str]
    material_ids: set[str]
    first_position: int


class KnowledgeListGenerator:
    content_type = "knowledge_list"

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
            params = KnowledgeListParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid knowledge-list parameters", status_code=422) from exc
        return run_material_coverage(
            batches=batches,
            expected_material_ids=set(expected_material_ids),
            map_batch=lambda batch: self.model_provider.generate_structured(
                prompt=build_knowledge_map_prompt(batch, parameters=params),
                output_schema=KnowledgeMapResult,
            ),
            reduce_results=lambda mapped: self._reduce(mapped, batches=batches, params=params),
        ).value

    def _reduce(
        self,
        mapped: list[KnowledgeMapResult],
        *,
        batches: tuple[MaterialContextBatch, ...],
        params: KnowledgeListParameters,
    ) -> GeneratorOutput:
        allowed = {chunk.chunk_id for batch in batches for chunk in batch.chunks}
        material_by_chunk = {chunk.chunk_id: chunk.material_id for batch in batches for chunk in batch.chunks}
        merged: dict[str, _MergedItem] = {}
        position = 0
        for result in mapped:
            for candidate in result.candidates:
                chunk_ids = list(dict.fromkeys(item for item in candidate.source_chunk_ids if item in allowed))
                if not chunk_ids:
                    continue
                key = _normalized(candidate.name)
                existing = merged.get(key)
                if existing is None:
                    merged[key] = _MergedItem(candidate, chunk_ids, {material_by_chunk[item] for item in chunk_ids}, position)
                    position += 1
                else:
                    if IMPORTANCE[candidate.importance] > IMPORTANCE[existing.candidate.importance]:
                        existing.candidate.importance = candidate.importance
                    if candidate.definition not in existing.candidate.definition:
                        existing.candidate.definition = (existing.candidate.definition + " " + candidate.definition)[:1200]
                    for chunk_id in chunk_ids:
                        if chunk_id not in existing.chunk_ids:
                            existing.chunk_ids.append(chunk_id)
                            existing.material_ids.add(material_by_chunk[chunk_id])
        minimum = IMPORTANCE[params.minimum_importance]
        items = [item for item in merged.values() if IMPORTANCE[item.candidate.importance] >= minimum]
        if not items:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Knowledge list is empty after filtering")
        focus = _normalized(params.focus) if params.focus else None
        items.sort(
            key=lambda item: (
                -IMPORTANCE[item.candidate.importance],
                0 if focus and focus in _normalized(item.candidate.name + " " + item.candidate.definition) else 1,
                -len(item.material_ids),
                item.first_position,
            )
        )
        items = items[: params.item_count]
        final: list[KnowledgeItem] = []
        bindings: dict[str, list[str]] = {}
        for index, item in enumerate(items, start=1):
            item_id = f"kp_{index:03d}"
            final.append(
                KnowledgeItem(
                    id=item_id,
                    name=item.candidate.name,
                    definition=item.candidate.definition,
                    importance=item.candidate.importance,
                    related_section=item.candidate.related_section,
                    source_citation_ids=[],
                    sort_order=index,
                )
            )
            bindings[item_id] = item.chunk_ids
        content = KnowledgeListContent(items=final)
        return GeneratorOutput(
            title=f"知识点清单（{len(final)}项）",
            content=None,
            content_json=content.model_dump(mode="json"),
            item_citation_chunk_ids=bindings,
        )


def build_generator(model_provider: ModelProvider) -> KnowledgeListGenerator:
    return KnowledgeListGenerator(model_provider=model_provider)
