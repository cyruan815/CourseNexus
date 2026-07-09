from __future__ import annotations

from app.integrations.model_provider.mock import MockModelProvider
from app.modules.material_context.schemas import ContextChunk


def test_mock_model_provider_returns_deterministic_answer() -> None:
    chunk = ContextChunk(
        material_id="mat_1",
        chunk_id="chk_1",
        material_name="notes.md",
        page=None,
        page_index=0,
        heading="Intro",
        content_text="Alpha",
    )

    answer = MockModelProvider().answer_question(question="What is Alpha?", context_chunks=[chunk])

    assert answer.answer_text == "Mock answer based on: Alpha"
    assert answer.citation_chunk_ids == ["chk_1"]
