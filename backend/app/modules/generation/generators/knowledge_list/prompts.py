from __future__ import annotations

from app.modules.generation.generators.knowledge_list.schemas import KnowledgeListParameters
from app.modules.material_context.schemas import MaterialContextBatch


def build_knowledge_map_prompt(batch: MaterialContextBatch, *, parameters: KnowledgeListParameters) -> str:
    chunks: list[str] = []
    for chunk in batch.chunks:
        location = chunk.page or (f"page_index={chunk.page_index}" if chunk.page_index is not None else "unknown")
        chunks.append(
            f"[chunk_id={chunk.chunk_id}] material={chunk.material_name} location={location} "
            f"heading={chunk.heading or ''}\n{chunk.content_text}"
        )
    return (
        "Extract grounded knowledge points using only supplied material. Every point must cite supplied "
        "chunk_id values. Importance must reflect explicit material emphasis, never invented exam frequency. "
        f"Extraction focus: {parameters.extraction_focus}. User focus: {parameters.focus or 'none'}.\n\n"
        + "\n\n".join(chunks)
    )
