from __future__ import annotations

from dataclasses import dataclass
from threading import Event

import pytest

from app.core.errors import CourseNexusError
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch


@dataclass(frozen=True)
class MappedReference:
    facts: list[str]
    citation_chunk_ids: list[str]


@dataclass(frozen=True)
class SetReference:
    citation_chunk_ids: set[str]


def test_coverage_runner_rejects_missing_material() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        run_material_coverage(
            batches=[_batch_for("m1", "c1")],
            expected_material_ids={"m1", "m2"},
            map_batch=lambda batch: MappedReference(facts=batch.material_ids, citation_chunk_ids=[]),
            reduce_results=lambda items: items,
        )

    assert exc_info.value.code == "MATERIAL_COVERAGE_INCOMPLETE"


def test_coverage_runner_maps_multiple_batches_and_unions_citation_ids() -> None:
    batches = [_batch_for("m1", "c1"), _batch_for("m2", "c2")]

    result = run_material_coverage(
        batches=batches,
        expected_material_ids={"m1", "m2"},
        map_batch=lambda batch: MappedReference(
            facts=[f"fact:{batch.material_ids[0]}"],
            citation_chunk_ids=[chunk.chunk_id for chunk in batch.chunks],
        ),
        reduce_results=lambda items: [fact for item in items for fact in item.facts],
    )

    assert result.value == ["fact:m1", "fact:m2"]
    assert result.processed_material_ids == {"m1", "m2"}
    assert result.citation_chunk_ids == {"c1", "c2"}


def test_coverage_runner_preserves_input_order_when_map_batches_finish_out_of_order() -> None:
    first_started = Event()
    second_finished = Event()
    completion_order: list[str] = []

    def map_batch(batch: MaterialContextBatch) -> MappedReference:
        material_id = batch.material_ids[0]
        if material_id == "m1":
            first_started.set()
            if not second_finished.wait(timeout=2):
                raise AssertionError("second batch did not finish first")
        else:
            if not first_started.wait(timeout=2):
                raise AssertionError("first batch did not start")
            second_finished.set()
        completion_order.append(material_id)
        return MappedReference(facts=[material_id], citation_chunk_ids=[])

    result = run_material_coverage(
        batches=[_batch_for("m1", "c1"), _batch_for("m2", "c2")],
        expected_material_ids={"m1", "m2"},
        map_batch=map_batch,
        reduce_results=lambda items: [fact for item in items for fact in item.facts],
        map_concurrency=2,
    )

    assert completion_order == ["m2", "m1"]
    assert result.value == ["m1", "m2"]


def test_coverage_runner_unions_set_citation_ids() -> None:
    result = run_material_coverage(
        batches=[_batch_for("m1", "c1")],
        expected_material_ids={"m1"},
        map_batch=lambda batch: SetReference(citation_chunk_ids={batch.chunks[0].chunk_id}),
        reduce_results=lambda _items: {"citation_chunk_ids": {"c2"}},
    )

    assert result.citation_chunk_ids == {"c1", "c2"}


def test_coverage_runner_propagates_stable_generation_errors() -> None:
    def fail(_batch: MaterialContextBatch):
        raise CourseNexusError(code="GENERATION_FAILED", message="模型失败", status_code=502)

    with pytest.raises(CourseNexusError) as exc_info:
        run_material_coverage(
            batches=[_batch_for("m1", "c1")],
            expected_material_ids={"m1"},
            map_batch=fail,
            reduce_results=lambda items: items,
        )

    assert exc_info.value.code == "GENERATION_FAILED"


def test_coverage_runner_maps_unexpected_map_errors_to_generation_failed() -> None:
    def fail(_batch: MaterialContextBatch):
        raise RuntimeError("bad prompt")

    with pytest.raises(CourseNexusError) as exc_info:
        run_material_coverage(
            batches=[_batch_for("m1", "c1")],
            expected_material_ids={"m1"},
            map_batch=fail,
            reduce_results=lambda items: items,
        )

    assert exc_info.value.code == "GENERATION_FAILED"


def test_coverage_runner_checks_coverage_before_reduce() -> None:
    reduced = False

    def reduce_results(items):
        nonlocal reduced
        reduced = True
        return items

    with pytest.raises(CourseNexusError):
        run_material_coverage(
            batches=[_batch_for("m1", "c1")],
            expected_material_ids={"m1", "m2"},
            map_batch=lambda batch: MappedReference(facts=batch.material_ids, citation_chunk_ids=[]),
            reduce_results=reduce_results,
        )

    assert reduced is False


def _batch_for(material_id: str, chunk_id: str) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[
            ContextChunk(
                material_id=material_id,
                chunk_id=chunk_id,
                chunk_index=0,
                material_name=f"{material_id}.txt",
                page=None,
                page_index=None,
                heading=None,
                content_text=f"text for {material_id}",
            )
        ],
        material_ids=[material_id],
        estimated_tokens=4,
    )
