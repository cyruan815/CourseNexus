from __future__ import annotations

from app.modules.generation.generators.flashcard.schemas import FlashcardParameters
from app.modules.material_context.schemas import MaterialContextBatch


def build_flashcard_map_prompt(
    batch: MaterialContextBatch, *, parameters: FlashcardParameters, candidate_budget: int
) -> str:
    chunks: list[str] = []
    for chunk in batch.chunks:
        location = chunk.page or (f"page_index={chunk.page_index}" if chunk.page_index is not None else "unknown")
        chunks.append(
            f"[chunk_id={chunk.chunk_id}] material={chunk.material_name} location={location} "
            f"heading={chunk.heading or ''}\n{chunk.content_text}"
        )
    return (
        "Extract atomic grounded flashcards from only the supplied material. Every card must cite supplied "
        "chunk_id values. Cover concepts, definitions, procedures, formula meanings, and confusions without "
        f"external facts. Return at most {candidate_budget} cards. Style: {parameters.card_style}. "
        f"Include formulas: {parameters.include_formulas}. Focus: {parameters.focus or 'none'}.\n\n"
        + "\n\n".join(chunks)
    )
