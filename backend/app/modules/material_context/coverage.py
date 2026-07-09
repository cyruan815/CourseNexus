from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.errors import CourseNexusError
from app.modules.material_context.schemas import MaterialContextBatch


MappedBatchT = TypeVar("MappedBatchT")
CoverageValueT = TypeVar("CoverageValueT")


@dataclass(frozen=True)
class CoverageRunResult(Generic[CoverageValueT]):
    value: CoverageValueT
    processed_material_ids: set[str]
    citation_chunk_ids: set[str]


def run_material_coverage(
    *,
    batches: Iterable[MaterialContextBatch],
    expected_material_ids: set[str],
    map_batch: Callable[[MaterialContextBatch], MappedBatchT],
    reduce_results: Callable[[list[MappedBatchT]], CoverageValueT],
) -> CoverageRunResult[CoverageValueT]:
    mapped_items: list[MappedBatchT] = []
    processed_material_ids: set[str] = set()
    citation_chunk_ids: set[str] = set()

    for batch in batches:
        processed_material_ids.update(batch.material_ids)
        try:
            mapped_item = map_batch(batch)
        except CourseNexusError:
            raise
        except Exception as exc:
            raise CourseNexusError(code="GENERATION_FAILED", message="材料批次生成失败", status_code=502) from exc

        mapped_items.append(mapped_item)
        citation_chunk_ids.update(_extract_citation_chunk_ids(mapped_item))

    if processed_material_ids != expected_material_ids:
        raise CourseNexusError(
            code="MATERIAL_COVERAGE_INCOMPLETE",
            message="材料覆盖不完整",
            status_code=409,
            details={
                "expected_material_ids": sorted(expected_material_ids),
                "processed_material_ids": sorted(processed_material_ids),
            },
        )

    try:
        value = reduce_results(mapped_items)
    except CourseNexusError:
        raise
    except Exception as exc:
        raise CourseNexusError(code="GENERATION_FAILED", message="材料批次归并失败", status_code=502) from exc

    citation_chunk_ids.update(_extract_citation_chunk_ids(value))
    return CoverageRunResult(
        value=value,
        processed_material_ids=processed_material_ids,
        citation_chunk_ids=citation_chunk_ids,
    )


def _extract_citation_chunk_ids(value: object) -> set[str]:
    citation_chunk_ids = getattr(value, "citation_chunk_ids", None)
    if citation_chunk_ids is None and isinstance(value, dict):
        citation_chunk_ids = value.get("citation_chunk_ids")
    if citation_chunk_ids is None:
        return set()
    if isinstance(citation_chunk_ids, str):
        return {citation_chunk_ids}
    if isinstance(citation_chunk_ids, Sequence):
        return {chunk_id for chunk_id in citation_chunk_ids if isinstance(chunk_id, str)}
    return set()
