from __future__ import annotations

from app.modules.generation.generators.outline.generator import OutlineGenerator
from app.modules.generation.generators.outline.schemas import OutlineMapResult
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _batch(material: str, chunk: str, text: str) -> MaterialContextBatch:
    return MaterialContextBatch(chunks=[ContextChunk(material_id=material, chunk_id=chunk, material_name=f"{material}.md", page=None, page_index=None, heading=None, content_text=text)], material_ids=[material], estimated_tokens=10)


def _section(title: str, chunk: str, order: str) -> dict[str, object]:
    return {"title": title, "summary": f"Summary of {title}", "review_suggestion": f"Review {title}", "source_order_key": order, "source_chunk_ids": [chunk]}


def test_generator_maps_all_batches_merges_titles_and_assigns_sections() -> None:
    provider = RecordingStructuredModelProvider(
        {"candidates": [_section("Processes", "c1", "001"), _section("Scheduling", "c1", "002")]},
        {"candidates": [_section(" processes ", "c2", "003"), _section("Paging", "c2", "004")]},
    )
    output = OutlineGenerator(model_provider=provider).generate(
        batches=(_batch("m1", "c1", "Processes"), _batch("m2", "c2", "Paging")),
        expected_material_ids=frozenset({"m1", "m2"}), parameters={"section_count": 3, "organization": "source_order"},
    )
    assert len(provider.calls) == 2
    assert all(schema is OutlineMapResult for _, schema in provider.calls)
    assert [section["id"] for section in output.content_json["sections"]] == ["sec_001", "sec_002", "sec_003"]
    assert [section["sort_order"] for section in output.content_json["sections"]] == [1, 2, 3]
    assert output.item_citation_chunk_ids["sec_001"] == ["c1", "c2"]
    assert output.content_json["sections"][0]["title"].startswith("1. ")
