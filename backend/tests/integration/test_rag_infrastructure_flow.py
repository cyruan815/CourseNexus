from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from llama_index.core.embeddings import BaseEmbedding
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.llama_index_chroma import LlamaIndexChromaRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.coverage import run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope
from app.modules.material_context.service import iter_material_context_batches, retrieve_relevant_context
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


class KeywordEmbedding(BaseEmbedding):
    keywords: tuple[str, ...] = ("eigenvalue", "matrix", "history", "outside")

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text)

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._embed(query)

    def _embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [1.0 if keyword in lowered else 0.0 for keyword in self.keywords]


@dataclass(frozen=True)
class BatchReference:
    material_ids: set[str]
    citation_chunk_ids: set[str]


def test_rag_infrastructure_upload_parse_index_retrieve_and_cover(tmp_path: Path) -> None:
    with _session() as db:
        user = register_user(db, UserCreate(username="alice", password="password123"))
        course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
        other_course = create_course(db, user.id, CourseCreate(name="World History"))
        storage_root = tmp_path / "uploads"
        rag_index = LlamaIndexChromaRagIndex(
            persist_path=tmp_path / "chroma",
            collection_name="flow_chunks",
            embed_model=KeywordEmbedding(),
        )

        math = _upload_and_parse(
            db,
            storage_root,
            user_id=user.id,
            course_id=course.id,
            filename="math.txt",
            content="Eigenvalue basis\n\nMatrix trace",
            rag_index=rag_index,
        )
        history = _upload_and_parse(
            db,
            storage_root,
            user_id=user.id,
            course_id=course.id,
            filename="history.txt",
            content="History of eigenvalue notation",
            rag_index=rag_index,
        )
        outside = _upload_and_parse(
            db,
            storage_root,
            user_id=user.id,
            course_id=other_course.id,
            filename="outside.txt",
            content="Outside eigenvalue record",
            rag_index=rag_index,
        )

        retrieved = retrieve_relevant_context(
            db,
            user_id=user.id,
            course_id=course.id,
            query="eigenvalue",
            material_scope=MaterialScope(),
            rag_index=rag_index,
            top_k=8,
        )

        assert retrieved.chunks
        assert {chunk.material_id for chunk in retrieved.chunks}.issubset({math.id, history.id})
        assert outside.id not in {chunk.material_id for chunk in retrieved.chunks}
        assert all(chunk.score is not None for chunk in retrieved.chunks)

        batches = list(
            iter_material_context_batches(
                db,
                user_id=user.id,
                course_id=course.id,
                material_scope=MaterialScope(
                    include_all_parsed_materials=False,
                    material_ids=[math.id, history.id],
                ),
                max_tokens=20,
            )
        )
        expected_material_ids = {math.id, history.id}
        source_chunk_ids = {chunk.id for chunk in _chunks_for_materials(db, expected_material_ids)}

        coverage = run_material_coverage(
            batches=batches,
            expected_material_ids=expected_material_ids,
            map_batch=_map_batch,
            reduce_results=lambda items: {
                "material_ids": set().union(*(item.material_ids for item in items)),
                "citation_chunk_ids": set().union(*(item.citation_chunk_ids for item in items)),
            },
        )

        assert coverage.processed_material_ids == expected_material_ids
        assert coverage.value["material_ids"] == expected_material_ids
        assert coverage.citation_chunk_ids == source_chunk_ids


@contextmanager
def _session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


def _upload_and_parse(
    db: Session,
    storage_root: Path,
    *,
    user_id: str,
    course_id: str,
    filename: str,
    content: str,
    rag_index: LlamaIndexChromaRagIndex,
) -> CourseMaterial:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        stream=BytesIO(content.encode("utf-8")),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=storage_root, max_file_size_bytes=4096),
    )
    return parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=storage_root,
    )


def _chunks_for_materials(db: Session, material_ids: set[str]) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id.in_(material_ids))
            .order_by(MaterialChunk.material_id.asc(), MaterialChunk.chunk_index.asc())
        ).scalars()
    )


def _map_batch(batch: MaterialContextBatch) -> BatchReference:
    return BatchReference(
        material_ids=set(batch.material_ids),
        citation_chunk_ids={chunk.chunk_id for chunk in batch.chunks},
    )
