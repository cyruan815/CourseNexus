from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Sequence

import chromadb
from llama_index.core import StorageContext
from llama_index.core.embeddings import BaseEmbedding, MockEmbedding
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
    VectorStoreQuery,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.rag.base import RagChunk, RagIndexRecord, RagScopeFilter, RetrievalHit


index_logger = get_logger("rag.index")
retrieve_logger = get_logger("rag.retrieve")
RECONCILIATION_PAGE_SIZE = 1_000


class LlamaIndexChromaRagIndex:
    def __init__(self, *, persist_path: str | Path, collection_name: str, embed_model: BaseEmbedding) -> None:
        self.persist_path = Path(persist_path)
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(collection_name)
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def clear(self) -> None:
        started_at = perf_counter()
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(self.collection_name)
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index_logger.info(
                "索引清理成功 | collection=%s cost_ms=%.2f",
                self.collection_name,
                (perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引清理失败", status_code=502) from exc

    def index_chunks(self, chunks: Sequence[RagChunk]) -> None:
        if not chunks:
            return
        started_at = perf_counter()
        try:
            nodes = [self._node_for_chunk(chunk) for chunk in chunks]
            embeddings = self.embed_model.get_text_embedding_batch([node.text for node in nodes])
            for node, embedding in zip(nodes, embeddings, strict=True):
                node.embedding = embedding
            self.collection.delete(ids=[node.node_id for node in nodes])
            self.vector_store.add(nodes)
            index_logger.info(
                "索引成功 | collection=%s chunks=%d cost_ms=%.2f",
                self.collection_name,
                len(chunks),
                (perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引失败", status_code=502) from exc

    def delete_material(self, material_id: str) -> None:
        self.delete_materials([material_id])

    def delete_materials(self, material_ids: Sequence[str]) -> None:
        unique_material_ids = list(dict.fromkeys(material_ids))
        if not unique_material_ids:
            return
        started_at = perf_counter()
        try:
            material_filter: str | dict[str, list[str]] = (
                unique_material_ids[0]
                if len(unique_material_ids) == 1
                else {"$in": unique_material_ids}
            )
            self.collection.delete(where={"material_id": material_filter})
            index_logger.info(
                "索引批量删除成功 | collection=%s materials=%d cost_ms=%.2f",
                self.collection_name,
                len(unique_material_ids),
                (perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引删除失败", status_code=502) from exc

    def delete_parse_version(self, parse_version_id: str) -> None:
        started_at = perf_counter()
        try:
            self.collection.delete(where={"parse_version_id": parse_version_id})
            index_logger.info(
                "解析版本索引删除成功 | collection=%s version=%s cost_ms=%.2f",
                self.collection_name,
                parse_version_id,
                (perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="解析版本索引删除失败", status_code=502) from exc

    def list_parse_version_chunk_ids(self, parse_version_id: str) -> set[str]:
        try:
            stored = self.collection.get(where={"parse_version_id": parse_version_id}, include=[])
            return set(stored.get("ids") or [])
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="解析版本索引校验失败", status_code=502) from exc

    def list_records(self) -> list[RagIndexRecord]:
        records: list[RagIndexRecord] = []
        offset = 0
        try:
            while True:
                stored = self.collection.get(
                    include=["metadatas"],
                    limit=RECONCILIATION_PAGE_SIZE,
                    offset=offset,
                )
                ids = stored.get("ids") or []
                metadatas = stored.get("metadatas") or []
                for chunk_id, metadata in zip(ids, metadatas, strict=False):
                    values = metadata or {}
                    records.append(
                        RagIndexRecord(
                            chunk_id=str(chunk_id),
                            user_id=_metadata_text(values.get("user_id")),
                            course_id=_metadata_text(values.get("course_id")),
                            material_id=_metadata_text(values.get("material_id")),
                            parse_version_id=_metadata_text(values.get("parse_version_id")),
                        )
                    )
                if len(ids) < RECONCILIATION_PAGE_SIZE:
                    break
                offset += len(ids)
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引对账读取失败", status_code=502) from exc
        return sorted(records, key=lambda item: item.chunk_id)

    def update_material_folder(self, material_id: str, folder_id: str | None) -> None:
        started_at = perf_counter()
        try:
            stored = self.collection.get(where={"material_id": material_id}, include=["metadatas"])
            ids = stored.get("ids") or []
            metadatas = stored.get("metadatas") or []
            if not ids:
                return
            self.collection.update(
                ids=ids,
                metadatas=[{**metadata, "folder_id": folder_id or ""} for metadata in metadatas],
            )
            index_logger.info(
                "索引目录更新成功 | collection=%s material=%s vectors=%d cost_ms=%.2f",
                self.collection_name,
                material_id,
                len(ids),
                (perf_counter() - started_at) * 1000,
            )
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料目录索引更新失败", status_code=502) from exc

    def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
        if top_k <= 0:
            return []
        started_at = perf_counter()
        try:
            query_embedding = self.embed_model.get_query_embedding(query)
            result = self.vector_store.query(
                VectorStoreQuery(
                    query_embedding=query_embedding,
                    similarity_top_k=top_k,
                    filters=self._filters_for_scope(scope),
                )
            )
            ids = result.ids or []
            similarities = result.similarities or []
            hits = [
                RetrievalHit(chunk_id=chunk_id, score=float(similarity))
                for chunk_id, similarity in zip(ids, similarities, strict=False)
            ]
            retrieve_logger.info(
                "检索完成 | course=%s top_k=%d hits=%d cost_ms=%.2f",
                scope.course_id,
                top_k,
                len(hits),
                (perf_counter() - started_at) * 1000,
            )
            return hits
        except Exception as exc:
            raise CourseNexusError(code="RETRIEVAL_FAILED", message="资料检索失败", status_code=502) from exc

    def _node_for_chunk(self, chunk: RagChunk) -> TextNode:
        return TextNode(
            id_=chunk.chunk_id,
            text=chunk.text,
            metadata={
                "user_id": chunk.user_id,
                "course_id": chunk.course_id,
                "material_id": chunk.material_id,
                "parse_version_id": chunk.parse_version_id or "",
                "folder_id": chunk.folder_id or "",
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page or "",
                "page_index": chunk.page_index if chunk.page_index is not None else -1,
                "heading": chunk.heading or "",
            },
        )

    def _filters_for_scope(self, scope: RagScopeFilter) -> MetadataFilters:
        filters = [
            MetadataFilter(key="user_id", value=scope.user_id, operator=FilterOperator.EQ),
            MetadataFilter(key="course_id", value=scope.course_id, operator=FilterOperator.EQ),
        ]
        if scope.material_ids:
            filters.append(
                MetadataFilter(key="material_id", value=list(scope.material_ids), operator=FilterOperator.IN)
            )
        if scope.chunk_ids:
            filters.append(
                MetadataFilter(key="chunk_id", value=list(scope.chunk_ids), operator=FilterOperator.IN)
            )
        return MetadataFilters(filters=filters, condition=FilterCondition.AND)


def create_openai_chroma_rag_index(
    *,
    persist_path: str | Path,
    collection_name: str,
    api_key: str,
    embedding_model: str,
    api_base_url: str | None = None,
) -> LlamaIndexChromaRagIndex:
    return LlamaIndexChromaRagIndex(
        persist_path=persist_path,
        collection_name=collection_name,
        embed_model=OpenAIEmbedding(
            model=embedding_model,
            api_key=api_key,
            api_base=api_base_url,
        ),
    )


def open_existing_chroma_rag_index(
    *,
    persist_path: str | Path,
    collection_name: str,
) -> LlamaIndexChromaRagIndex | None:
    path = Path(persist_path)
    if not (path / "chroma.sqlite3").is_file():
        return None
    try:
        client = chromadb.PersistentClient(path=str(path))
        collection_names = {
            collection.name if hasattr(collection, "name") else str(collection)
            for collection in client.list_collections()
        }
        if collection_name not in collection_names:
            return None
        return LlamaIndexChromaRagIndex(
            persist_path=path,
            collection_name=collection_name,
            embed_model=MockEmbedding(embed_dim=1),
        )
    except Exception as exc:
        raise CourseNexusError(code="INDEXING_FAILED", message="资料索引对账打开失败", status_code=502) from exc


def _metadata_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
