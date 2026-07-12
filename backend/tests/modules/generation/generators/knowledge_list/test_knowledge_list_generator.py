from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.modules.generation.generators.knowledge_list.generator import KnowledgeListGenerator
from app.modules.generation.generators.knowledge_list.schemas import KnowledgeMapResult
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _batch(material: str, chunk: str, text: str) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[
            ContextChunk(
                material_id=material,
                chunk_id=chunk,
                material_name=f"{material}.md",
                page=None,
                page_index=None,
                heading=None,
                content_text=text,
            )
        ],
        material_ids=[material],
        estimated_tokens=10,
    )


def _item(name: str, chunk: str, importance: str = "medium") -> dict[str, object]:
    return {
        "name": name,
        "definition": f"Definition of {name}",
        "importance": importance,
        "related_section": "Core",
        "source_chunk_ids": [chunk],
    }


def test_generator_maps_all_batches_merges_and_orders_by_importance() -> None:
    provider = RecordingStructuredModelProvider(
        {"candidates": [_item("Process", "c1", "medium"), _item("Scheduling", "c1", "low")]},
        {"candidates": [_item(" process ", "c2", "high"), _item("Paging", "c2", "medium")]},
    )
    output = KnowledgeListGenerator(model_provider=provider).generate(
        batches=(_batch("m1", "c1", "Process"), _batch("m2", "c2", "Paging")),
        expected_material_ids=frozenset({"m1", "m2"}),
        parameters={"item_count": 3},
    )
    assert len(provider.calls) == 2
    assert all(schema is KnowledgeMapResult for _, schema in provider.calls)
    assert [item["id"] for item in output.content_json["items"]] == [
        "kp_001",
        "kp_002",
        "kp_003",
    ]
    assert output.content_json["items"][0]["name"] == "Process"
    assert output.content_json["items"][0]["importance"] == "high"
    assert output.item_citation_chunk_ids["kp_001"] == ["c1", "c2"]


def test_minimum_importance_empty_result_is_schema_invalid() -> None:
    provider = RecordingStructuredModelProvider({"candidates": [_item("Minor", "c1", "low")]})
    with pytest.raises(CourseNexusError) as exc_info:
        KnowledgeListGenerator(model_provider=provider).generate(
            batches=(_batch("m1", "c1", "Minor"),),
            expected_material_ids=frozenset({"m1"}),
            parameters={"minimum_importance": "high"},
        )
    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
