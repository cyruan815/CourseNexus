from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    user_id: str
    course_id: str
    material_id: str
    folder_id: str | None
    chunk_index: int
    text: str
    page: str | None
    page_index: int | None
    heading: str | None


@dataclass(frozen=True)
class RagScopeFilter:
    user_id: str
    course_id: str
    material_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    score: float


class RagIndex(Protocol):
    def clear(self) -> None:
        """Remove all derived records from the configured retrieval collection."""

    def index_chunks(self, chunks: Sequence[RagChunk]) -> None:
        """Index or upsert chunks into a derived retrieval store."""

    def delete_material(self, material_id: str) -> None:
        """Remove all derived records for one material."""

    def update_material_folder(self, material_id: str, folder_id: str | None) -> None:
        """Update folder metadata without recomputing embeddings."""

    def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
        """Retrieve scored chunk ids inside a hard scope filter."""
