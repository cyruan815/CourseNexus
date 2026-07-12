from __future__ import annotations

from app.modules.generation.generators.quiz.schemas import QuizParameters
from app.modules.material_context.schemas import MaterialContextBatch


def build_quiz_map_prompt(
    batch: MaterialContextBatch, *, parameters: QuizParameters, candidate_budget: int
) -> str:
    chunks: list[str] = []
    for chunk in batch.chunks:
        location = chunk.page or (f"page_index={chunk.page_index}" if chunk.page_index is not None else "unknown")
        chunks.append(
            f"[chunk_id={chunk.chunk_id}] material={chunk.material_name} location={location} "
            f"heading={chunk.heading or ''}\n{chunk.content_text}"
        )
    return (
        "Generate grounded single-choice course self-test candidates using only the supplied material. "
        "Every candidate must cite supplied chunk_id values. Do not use external facts. "
        "Each question must have exactly four options A-D, exactly one correct option, and a concise explanation. "
        f"Return at most {candidate_budget} candidates. Allowed types: {parameters.question_types}. "
        f"Requested difficulty: {parameters.difficulty}. Focus: {parameters.focus or 'none'}.\n\n"
        + "\n\n".join(chunks)
    )
