from __future__ import annotations

import logging
from pathlib import Path

import pytest
from llama_index.core.embeddings import BaseEmbedding

from app.core.errors import CourseNexusError
from app.integrations.rag.base import RagChunk, RagScopeFilter
from app.integrations.rag.llama_index_chroma import LlamaIndexChromaRagIndex


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


class KeywordEmbedding(BaseEmbedding):
    keywords: tuple[str, ...] = ("matrix", "history", "eigenvalue", "folder", "updated")

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in self.keywords]


class FailingEmbedding(KeywordEmbedding):
    def _get_text_embedding(self, text: str) -> list[float]:
        raise RuntimeError("embedding failed")

    def _get_query_embedding(self, query: str) -> list[float]:
        raise RuntimeError("retrieval failed")


def rag_chunk(
    chunk_id: str,
    *,
    user_id: str = "u1",
    course_id: str = "math",
    material_id: str = "m1",
    folder_id: str | None = None,
    chunk_index: int = 0,
    text: str = "matrix eigenvalue",
) -> RagChunk:
    return RagChunk(
        chunk_id=chunk_id,
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        folder_id=folder_id,
        chunk_index=chunk_index,
        text=text,
        page="1",
        page_index=0,
        heading="A",
    )


def math_chunk(text: str = "matrix eigenvalue") -> RagChunk:
    return rag_chunk("math-c1", text=text, material_id="math-m1")


def history_chunk() -> RagChunk:
    return rag_chunk("history-c1", course_id="history", material_id="history-m1", text="history")


def index(tmp_path: Path) -> LlamaIndexChromaRagIndex:
    return LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="test_chunks",
        embed_model=KeywordEmbedding(),
    )


def test_chroma_persists_and_filters_course(tmp_path: Path, caplog) -> None:
    logger = capture_course_logs(caplog)
    first = index(tmp_path)
    try:
        first.index_chunks([math_chunk(), history_chunk()])

        reopened = index(tmp_path)
        hits = reopened.retrieve(
            query="matrix",
            scope=RagScopeFilter(user_id="u1", course_id="math"),
            top_k=8,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert [hit.chunk_id for hit in hits] == ["math-c1"]
    index_record = next(record for record in caplog.records if record.name.endswith("rag.index"))
    retrieve_record = next(record for record in caplog.records if record.name.endswith("rag.retrieve"))
    assert "索引成功" in index_record.getMessage()
    assert "chunks=2" in index_record.getMessage()
    assert "检索完成" in retrieve_record.getMessage()
    assert "hits=1" in retrieve_record.getMessage()
    assert "matrix eigenvalue" not in index_record.getMessage()
    assert "query=matrix" not in retrieve_record.getMessage()


def test_chroma_filters_user_and_material(tmp_path: Path) -> None:
    rag_index = index(tmp_path)
    rag_index.index_chunks(
        [
            rag_chunk("u1-f1", user_id="u1", material_id="m1", folder_id="f1", text="matrix folder"),
            rag_chunk("u1-f2", user_id="u1", material_id="m2", folder_id="f2", text="matrix folder"),
            rag_chunk("u2-f2", user_id="u2", material_id="m2", folder_id="f2", text="matrix folder"),
        ]
    )

    hits = rag_index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math", material_ids=("m2",)),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["u1-f2"]


def test_chroma_repeat_upsert_replaces_existing_chunk(tmp_path: Path) -> None:
    rag_index = index(tmp_path)
    rag_index.index_chunks(
        [
            math_chunk("matrix"),
            rag_chunk("math-c2", material_id="math-m2", text="matrix"),
        ]
    )
    rag_index.index_chunks([math_chunk("history updated")])

    matrix_hits = rag_index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=1,
    )
    updated_hits = rag_index.retrieve(
        query="updated",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=1,
    )
    stored = rag_index.collection.get(ids=["math-c1"], include=["documents"])

    assert [hit.chunk_id for hit in matrix_hits] == ["math-c2"]
    assert [hit.chunk_id for hit in updated_hits] == ["math-c1"]
    assert stored["documents"] == ["history updated"]


def test_chroma_delete_material_removes_vectors(tmp_path: Path) -> None:
    rag_index = index(tmp_path)
    rag_index.index_chunks([rag_chunk("c1", material_id="m1"), rag_chunk("c2", material_id="m2")])

    rag_index.delete_material("m1")

    hits = rag_index.retrieve(
        query="matrix",
        scope=RagScopeFilter(user_id="u1", course_id="math"),
        top_k=8,
    )

    assert [hit.chunk_id for hit in hits] == ["c2"]


def test_chroma_updates_material_folder_without_reembedding(tmp_path: Path) -> None:
    rag_index = index(tmp_path)
    rag_index.index_chunks([rag_chunk("c1", material_id="m1", folder_id="old")])

    rag_index.update_material_folder("m1", "new")

    stored = rag_index.collection.get(ids=["c1"], include=["metadatas"])

    assert stored["metadatas"] is not None
    assert stored["metadatas"][0]["folder_id"] == "new"


def test_chroma_clear_only_removes_configured_collection(tmp_path: Path) -> None:
    primary = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="primary_chunks",
        embed_model=KeywordEmbedding(),
    )
    unrelated = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="unrelated_chunks",
        embed_model=KeywordEmbedding(),
    )
    primary.index_chunks([math_chunk()])
    unrelated.index_chunks([rag_chunk("unrelated-c1", text="matrix", material_id="unrelated-m1")])

    primary.clear()

    primary_hits = primary.retrieve(query="matrix", scope=RagScopeFilter(user_id="u1", course_id="math"), top_k=8)
    unrelated_hits = unrelated.retrieve(query="matrix", scope=RagScopeFilter(user_id="u1", course_id="math"), top_k=8)

    assert primary_hits == []
    assert [hit.chunk_id for hit in unrelated_hits] == ["unrelated-c1"]


def test_chroma_maps_indexing_errors(tmp_path: Path) -> None:
    rag_index = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="test_chunks",
        embed_model=FailingEmbedding(),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        rag_index.index_chunks([math_chunk()])

    assert exc_info.value.code == "INDEXING_FAILED"
    assert exc_info.value.status_code == 502
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_chroma_maps_retrieval_errors(tmp_path: Path) -> None:
    rag_index = index(tmp_path)
    rag_index.index_chunks([math_chunk()])
    rag_index_with_failure = LlamaIndexChromaRagIndex(
        persist_path=tmp_path,
        collection_name="test_chunks",
        embed_model=FailingEmbedding(),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        rag_index_with_failure.retrieve(
            query="matrix",
            scope=RagScopeFilter(user_id="u1", course_id="math"),
            top_k=8,
        )

    assert exc_info.value.code == "RETRIEVAL_FAILED"
    assert exc_info.value.status_code == 502
    assert isinstance(exc_info.value.__cause__, RuntimeError)
