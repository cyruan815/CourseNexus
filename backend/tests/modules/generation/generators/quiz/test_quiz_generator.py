from __future__ import annotations

from app.modules.generation.generators.quiz.generator import QuizGenerator
from app.modules.generation.generators.quiz.schemas import QuizMapResult
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _batch(material: str, chunk: str, text: str) -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[ContextChunk(material_id=material, chunk_id=chunk, material_name=f"{material}.md", page=None, page_index=None, heading=None, content_text=text)],
        material_ids=[material], estimated_tokens=10,
    )


def _choice(question: str, chunk: str) -> dict[str, object]:
    return {
        "question_type": "single_choice",
        "question_text": question,
        "options": [
            {"id": "A", "text": "Answer"},
            {"id": "B", "text": "Distractor B"},
            {"id": "C", "text": "Distractor C"},
            {"id": "D", "text": "Distractor D"},
        ],
        "correct_answer": "A",
        "explanation": "Grounded explanation",
        "difficulty": "medium",
        "source_chunk_ids": [chunk],
    }


def test_generator_maps_every_batch_deduplicates_and_assigns_stable_ids() -> None:
    provider = RecordingStructuredModelProvider(
        {"candidates": [_choice("Define process", "c1"), _choice("What is scheduling?", "c1")]},
        {"candidates": [_choice(" define PROCESS ", "c2"), _choice("What is paging?", "c2")]},
    )
    output = QuizGenerator(model_provider=provider).generate(
        batches=(_batch("m1", "c1", "Processes"), _batch("m2", "c2", "Paging")),
        expected_material_ids=frozenset({"m1", "m2"}),
        parameters={"question_count": 3, "question_types": ["single_choice"]},
    )
    assert len(provider.calls) == 2
    assert all(schema is QuizMapResult for _, schema in provider.calls)
    assert [item["id"] for item in output.content_json["questions"]] == ["q_001", "q_002", "q_003"]
    assert [item["sort_order"] for item in output.content_json["questions"]] == [1, 2, 3]
    assert output.item_citation_chunk_ids["q_001"] == ["c1", "c2"]
