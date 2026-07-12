from __future__ import annotations

from app.modules.generation.generators.outline.schemas import OutlineParameters
from app.modules.material_context.schemas import MaterialContextBatch


def build_outline_map_prompt(batch: MaterialContextBatch, *, parameters: OutlineParameters) -> str:
    chunks=[]
    for chunk in batch.chunks:
        location=chunk.page or (f"page_index={chunk.page_index}" if chunk.page_index is not None else "unknown")
        chunks.append(f"[chunk_id={chunk.chunk_id}] material={chunk.material_name} location={location} heading={chunk.heading or ''}\n{chunk.content_text}")
    return (
        "Extract grounded review-outline section candidates from only the supplied material. Every section must cite supplied chunk IDs. "
        f"Organization target: {parameters.organization}. Review goal: {parameters.review_goal or 'none'}. Detail: {parameters.detail_level}.\n\n"
        + "\n\n".join(chunks)
    )
