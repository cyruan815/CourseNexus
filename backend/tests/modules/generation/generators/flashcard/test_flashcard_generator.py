from __future__ import annotations

from app.modules.generation.generators.flashcard.generator import FlashcardGenerator
from app.modules.generation.generators.flashcard.schemas import FlashcardMapResult
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _batch(material: str, chunk: str, text: str) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[ContextChunk(material_id=material, chunk_id=chunk, material_name=f"{material}.md", page=None, page_index=None, heading=None, content_text=text)],
        material_ids=[material], estimated_tokens=10,
    )


def _card(front: str, chunk: str, *, tags: list[str] | None = None) -> dict[str, object]:
    return {"front": front, "back": f"Answer for {front}", "tags": tags or ["core"], "source_chunk_ids": [chunk]}


def test_generator_maps_all_batches_merges_duplicates_and_assigns_ids() -> None:
    provider = RecordingStructuredModelProvider(
        {"candidates": [_card("What is a process?", "c1", tags=["os"]), _card("Scheduling", "c1")]},
        {"candidates": [_card(" what IS a PROCESS? ", "c2", tags=["process"]), _card("Paging", "c2")]},
    )
    output = FlashcardGenerator(model_provider=provider).generate(
        batches=(_batch("m1", "c1", "Processes"), _batch("m2", "c2", "Paging")),
        expected_material_ids=frozenset({"m1", "m2"}), parameters={"card_count": 3},
    )
    assert len(provider.calls) == 2
    assert all(schema is FlashcardMapResult for _, schema in provider.calls)
    assert [card["id"] for card in output.content_json["cards"]] == ["card_001", "card_002", "card_003"]
    assert all(card["mastery_status"] == "unknown" for card in output.content_json["cards"])
    assert output.item_citation_chunk_ids["card_001"] == ["c1", "c2"]
