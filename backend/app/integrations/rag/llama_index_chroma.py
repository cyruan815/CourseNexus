from __future__ import annotations

from pathlib import Path
from typing import Sequence

import chromadb
from llama_index.core import StorageContext
from llama_index.core.embeddings import BaseEmbedding
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
from app.integrations.rag.base import RagChunk, RagScopeFilter, RetrievalHit


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
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(self.collection_name)
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引清理失败", status_code=502) from exc

    def index_chunks(self, chunks: Sequence[RagChunk]) -> None:
        if not chunks:
            return
        try:
            nodes = [self._node_for_chunk(chunk) for chunk in chunks]
            embeddings = self.embed_model.get_text_embedding_batch([node.text for node in nodes])
            for node, embedding in zip(nodes, embeddings, strict=True):
                node.embedding = embedding
            self.collection.delete(ids=[node.node_id for node in nodes])
            self.vector_store.add(nodes)
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引失败", status_code=502) from exc

    def delete_material(self, material_id: str) -> None:
        try:
            self.collection.delete(where={"material_id": material_id})
        except Exception as exc:
            raise CourseNexusError(code="INDEXING_FAILED", message="资料索引删除失败", status_code=502) from exc

    def retrieve(self, *, query: str, scope: RagScopeFilter, top_k: int) -> list[RetrievalHit]:
        if top_k <= 0:
            return []
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
            return [
                RetrievalHit(chunk_id=chunk_id, score=float(similarity))
                for chunk_id, similarity in zip(ids, similarities, strict=False)
            ]
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
        if scope.folder_ids:
            filters.append(MetadataFilter(key="folder_id", value=list(scope.folder_ids), operator=FilterOperator.IN))
        return MetadataFilters(filters=filters, condition=FilterCondition.AND)


def create_openai_chroma_rag_index(
    *,
    persist_path: str | Path,
    collection_name: str,
    api_key: str,
    embedding_model: str,
) -> LlamaIndexChromaRagIndex:
    return LlamaIndexChromaRagIndex(
        persist_path=persist_path,
        collection_name=collection_name,
        embed_model=OpenAIEmbedding(
            model=embedding_model,
            api_key=api_key,
        ),
    )
