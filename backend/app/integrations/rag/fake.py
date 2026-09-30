from __future__ import annotations

from dataclasses import replace
import re
from typing import Sequence

from app.integrations.rag.base import RagChunk, RagScopeFilter, RetrievalHit


TOKEN_PATTERN = re.compile(r"[\w]+", re.UNICODE)


class FakeRagIndex:
    def __init__(self) -> None:
        self.records: dict[str, RagChunk] = {}

    @classmethod
    def from_chunks(cls, chunks: Sequence[RagChunk]) -> "FakeRagIndex":
        index = cls()
        index.index_chunks(chunks)
        return index

    def index_chunks(self, chunks: Sequence[RagChunk]) -> None:
        for chunk in chunks:
            self.records[chunk.chunk_id] = chunk

    def clear(self) -> None:
        self.records = {}

    def delete_material(self, material_id: str) -> None:
        self.delete_materials([material_id])

    def delete_materials(self, material_ids: Sequence[str]) -> None:
        deleted_ids = set(material_ids)
        self.records = {
            chunk_id: chunk
            for chunk_id, chunk in self.records.items()
            if chunk.material_id not in deleted_ids
        }

    def delete_parse_version(self, parse_version_id: str) -> None:
        self.records = {
            chunk_id: chunk
            for chunk_id, chunk in self.records.items()
            if chunk.parse_version_id != parse_version_id
        }

    def list_parse_version_chunk_ids(self, parse_version_id: str) -> set[str]:
        return {
            chunk_id
            for chunk_id, chunk in self.records.items()
            if chunk.parse_version_id == parse_version_id
        }

    def update_material_folder(self, material_id: str, folder_id: str | None) -> None:
        self.records = {
            chunk_id: replace(chunk, folder_id=folder_id) if chunk.material_id == material_id else chunk
            for chunk_id, chunk in self.records.items()
        }

    def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
        query_tokens = self._tokens(query)
        if not query_tokens or top_k <= 0:
            return []

        ranked: list[tuple[float, int, str]] = []
        for chunk in self.records.values():
            if not self._in_scope(chunk, scope):
                continue
            score = self._score(query_tokens, chunk.text)
            if score <= 0:
                continue
            ranked.append((score, chunk.chunk_index, chunk.chunk_id))

        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        return [RetrievalHit(chunk_id=chunk_id, score=score) for score, _, chunk_id in ranked[:top_k]]

    def _in_scope(self, chunk: RagChunk, scope: RagScopeFilter) -> bool:
        if chunk.user_id != scope.user_id or chunk.course_id != scope.course_id:
            return False
        if scope.material_ids and chunk.material_id not in scope.material_ids:
            return False
        return True

    def _score(self, query_tokens: set[str], text: str) -> float:
        text_tokens = self._tokens(text)
        if not text_tokens:
            return 0.0
        overlap = query_tokens & text_tokens
        return len(overlap) / len(query_tokens)

    def _tokens(self, text: str) -> set[str]:
        return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)}
