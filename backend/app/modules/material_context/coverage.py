from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.errors import CourseNexusError
from app.modules.material_context.schemas import MaterialContextBatch


MappedBatchT = TypeVar("MappedBatchT")
CoverageValueT = TypeVar("CoverageValueT")


@dataclass(frozen=True)
class CoverageMapResult(Generic[MappedBatchT]):
    mapped_items: list[MappedBatchT]
    processed_material_ids: set[str]
    citation_chunk_ids: set[str]


@dataclass(frozen=True)
class CoverageRunResult(Generic[CoverageValueT]):
    value: CoverageValueT
    processed_material_ids: set[str]
    citation_chunk_ids: set[str]


def map_material_coverage_batches(
    *,
    batches: Iterable[MaterialContextBatch],
    expected_material_ids: set[str],
    map_batch: Callable[[MaterialContextBatch], MappedBatchT],
    map_concurrency: int = 1,
) -> CoverageMapResult[MappedBatchT]:
    if map_concurrency < 1:
        raise ValueError("map_concurrency must be at least 1")

    batch_list = list(batches)
    processed_material_ids = {
        material_id
        for batch in batch_list
        for material_id in batch.material_ids
    }

    if map_concurrency == 1:
        mapped_items = [_map_one_batch(batch, map_batch) for batch in batch_list]
    else:
        mapped_items = [None] * len(batch_list)
        with ThreadPoolExecutor(max_workers=map_concurrency) as executor:
            futures = {
                executor.submit(_map_one_batch, batch, map_batch): index
                for index, batch in enumerate(batch_list)
            }
            try:
                for future in as_completed(futures):
                    mapped_items[futures[future]] = future.result()
            except BaseException:
                for future in futures:
                    future.cancel()
                raise

    citation_chunk_ids: set[str] = set()
    for mapped_item in mapped_items:
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

    return CoverageMapResult(
        mapped_items=mapped_items,
        processed_material_ids=processed_material_ids,
        citation_chunk_ids=citation_chunk_ids,
    )


def reduce_material_coverage(
    *,
    mapped_result: CoverageMapResult[MappedBatchT],
    reduce_results: Callable[[list[MappedBatchT]], CoverageValueT],
) -> CoverageRunResult[CoverageValueT]:
    try:
        value = reduce_results(mapped_result.mapped_items)
    except CourseNexusError:
        raise
    except Exception as exc:
        raise CourseNexusError(code="GENERATION_FAILED", message="材料批次归并失败", status_code=502) from exc

    citation_chunk_ids = set(mapped_result.citation_chunk_ids)
    citation_chunk_ids.update(_extract_citation_chunk_ids(value))
    return CoverageRunResult(
        value=value,
        processed_material_ids=set(mapped_result.processed_material_ids),
        citation_chunk_ids=citation_chunk_ids,
    )


def run_material_coverage(
    *,
    batches: Iterable[MaterialContextBatch],
    expected_material_ids: set[str],
    map_batch: Callable[[MaterialContextBatch], MappedBatchT],
    reduce_results: Callable[[list[MappedBatchT]], CoverageValueT],
    map_concurrency: int = 1,
) -> CoverageRunResult[CoverageValueT]:
    mapped_result = map_material_coverage_batches(
        batches=batches,
        expected_material_ids=expected_material_ids,
        map_batch=map_batch,
        map_concurrency=map_concurrency,
    )
    return reduce_material_coverage(mapped_result=mapped_result, reduce_results=reduce_results)


def _map_one_batch(
    batch: MaterialContextBatch,
    map_batch: Callable[[MaterialContextBatch], MappedBatchT],
) -> MappedBatchT:
    try:
        return map_batch(batch)
    except CourseNexusError:
        raise
    except Exception as exc:
        raise CourseNexusError(code="GENERATION_FAILED", message="材料批次生成失败", status_code=502) from exc


def _extract_citation_chunk_ids(value: object) -> set[str]:
    citation_chunk_ids = getattr(value, "citation_chunk_ids", None)
    if citation_chunk_ids is None and isinstance(value, dict):
        citation_chunk_ids = value.get("citation_chunk_ids")
    if citation_chunk_ids is None:
        return set()
    if isinstance(citation_chunk_ids, str):
        return {citation_chunk_ids}
    if isinstance(citation_chunk_ids, Iterable):
        return {chunk_id for chunk_id in citation_chunk_ids if isinstance(chunk_id, str)}
    return set()
