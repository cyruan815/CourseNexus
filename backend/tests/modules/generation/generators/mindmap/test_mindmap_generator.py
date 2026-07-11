from __future__ import annotations

from app.modules.generation.generators.mindmap.generator import MindmapGenerator
from app.modules.generation.generators.mindmap.schemas import MindmapMapResult
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _batch(material: str, chunk: str, text: str) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[ContextChunk(material_id=material, chunk_id=chunk, material_name=f"{material}.md", page=None, page_index=None, heading=None, content_text=text)],
        material_ids=[material], estimated_tokens=10,
    )


def test_generator_maps_all_batches_and_builds_markdown() -> None:
    provider = RecordingStructuredModelProvider(
        {"concepts": [
            {"local_key": "root", "label": "Operating Systems", "summary": "Root", "parent_local_key": None, "source_chunk_ids": ["c1"]},
            {"local_key": "process", "label": "Processes", "summary": "Process", "parent_local_key": "root", "source_chunk_ids": ["c1"]},
        ], "relations": []},
        {"concepts": [
            {"local_key": "root2", "label": "Operating Systems", "summary": "Root", "parent_local_key": None, "source_chunk_ids": ["c2"]},
            {"local_key": "memory", "label": "Memory", "summary": "Memory", "parent_local_key": "root2", "source_chunk_ids": ["c2"]},
        ], "relations": []},
    )
    generator = MindmapGenerator(model_provider=provider)
    output = generator.generate(
        batches=(_batch("m1", "c1", "Processes"), _batch("m2", "c2", "Memory")),
        expected_material_ids=frozenset({"m1", "m2"}), parameters={"center_topic": "Operating Systems"},
    )
    assert len(provider.calls) == 2
    assert all(schema is MindmapMapResult for _, schema in provider.calls)
    assert [node["id"] for node in output.content_json["nodes"]] == ["node_001", "node_002", "node_003"]
    assert output.content_json["markmap_markdown"] == "- Operating Systems\n  - Processes\n  - Memory"
    assert output.item_citation_chunk_ids["node_002"] == ["c1"]
    assert output.item_citation_chunk_ids["node_003"] == ["c2"]
