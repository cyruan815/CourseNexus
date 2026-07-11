from __future__ import annotations

from app.modules.material_context.schemas import MaterialContextBatch


def build_mindmap_map_prompt(batch: MaterialContextBatch, *, center_topic: str | None) -> str:
    chunks = []
    for chunk in batch.chunks:
        location = chunk.page or (f"page_index={chunk.page_index}" if chunk.page_index is not None else "unknown")
        chunks.append(
            f"[chunk_id={chunk.chunk_id}] material={chunk.material_name} location={location} "
            f"heading={chunk.heading or ''}\n{chunk.content_text}"
        )
    topic = center_topic or "Select the most central grounded concept"
    return (
        "Extract a local mindmap from only the supplied course material. "
        "Do not add external facts. Every concept must cite supplied chunk_id values. "
        "Use stable local_key values, parent_local_key for hierarchy, and explicit related relations only. "
        f"Preferred center topic: {topic}.\n\n" + "\n\n".join(chunks)
    )
