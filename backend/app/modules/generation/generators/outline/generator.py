from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.outline.prompts import build_outline_map_prompt
from app.modules.generation.generators.outline.schemas import OutlineCandidate, OutlineContent, OutlineMapResult, OutlineParameters, OutlineSection
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch


def _normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


@dataclass
class _MergedSection:
    candidate: OutlineCandidate
    chunk_ids: list[str]
    material_ids: set[str]
    first_position: int


class OutlineGenerator:
    content_type="outline"
    def __init__(self, *, model_provider: ModelProvider) -> None:
        self.model_provider=model_provider

    def generate(self, *, batches: tuple[MaterialContextBatch, ...], expected_material_ids: frozenset[str], parameters: dict[str, Any]) -> GeneratorOutput:
        try:
            params=OutlineParameters.model_validate(parameters)
        except ValidationError as exc:
            raise CourseNexusError(code="VALIDATION_ERROR", message="Invalid outline parameters", status_code=422) from exc
        return run_material_coverage(
            batches=batches, expected_material_ids=set(expected_material_ids),
            map_batch=lambda batch: self.model_provider.generate_structured(prompt=build_outline_map_prompt(batch, parameters=params), output_schema=OutlineMapResult),
            reduce_results=lambda mapped: self._reduce(mapped, batches=batches, params=params),
        ).value

    def _reduce(self, mapped: list[OutlineMapResult], *, batches: tuple[MaterialContextBatch, ...], params: OutlineParameters) -> GeneratorOutput:
        allowed={chunk.chunk_id for batch in batches for chunk in batch.chunks}
        material_by_chunk={chunk.chunk_id:chunk.material_id for batch in batches for chunk in batch.chunks}
        merged: dict[str,_MergedSection]={}
        position=0
        for result in mapped:
            for candidate in result.candidates:
                chunk_ids=list(dict.fromkeys(item for item in candidate.source_chunk_ids if item in allowed))
                if not chunk_ids: continue
                key=_normalized(candidate.title)
                existing=merged.get(key)
                if existing is None:
                    merged[key]=_MergedSection(candidate,chunk_ids,{material_by_chunk[item] for item in chunk_ids},position); position+=1
                else:
                    for item in chunk_ids:
                        if item not in existing.chunk_ids:
                            existing.chunk_ids.append(item); existing.material_ids.add(material_by_chunk[item])
        if not merged:
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="Outline result is empty")
        items=list(merged.values())
        if params.organization=="source_order": items.sort(key=lambda item:(item.candidate.source_order_key,item.first_position))
        elif params.organization=="topic": items.sort(key=lambda item:(_normalized(item.candidate.title),item.first_position))
        else: items.sort(key=lambda item:(-len(item.material_ids),item.first_position))
        items=items[:params.section_count]
        limit={"concise":300,"standard":800,"detailed":2000}[params.detail_level]
        sections=[]; bindings={}
        for index,item in enumerate(items,start=1):
            section_id=f"sec_{index:03d}"
            sections.append(OutlineSection(id=section_id,title=f"{index}. {item.candidate.title.strip()}",summary=item.candidate.summary[:limit],review_suggestion=item.candidate.review_suggestion,source_citation_ids=[],sort_order=index))
            bindings[section_id]=item.chunk_ids
        content=OutlineContent(sections=sections)
        return GeneratorOutput(title=f"复习提纲（{len(sections)}节）",content=None,content_json=content.model_dump(mode="json"),item_citation_chunk_ids=bindings)


def build_generator(model_provider: ModelProvider) -> OutlineGenerator:
    return OutlineGenerator(model_provider=model_provider)
