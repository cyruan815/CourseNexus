from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.base import ModelAnswer
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.coverage import CoverageRunResult, run_material_coverage
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope
from app.modules.material_context.service import iter_material_context_batches, retrieve_relevant_context
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@dataclass
class ContractSeed:
    user: User
    course: Course
    math_material: CourseMaterial
    history_material: CourseMaterial
    math_chunks: list[MaterialChunk]
    history_chunks: list[MaterialChunk]
    rag_index: FakeRagIndex


@dataclass(frozen=True)
class ReferenceBatchOutput:
    facts: list[str]
    citation_chunk_ids: list[str]


class ReferenceQuestionModel:
    def __init__(self, citation_chunk_ids: list[str]) -> None:
        self.citation_chunk_ids = citation_chunk_ids

    def answer_question(self, *, question: str, context_chunks) -> ModelAnswer:
        return ModelAnswer(answer_text=f"answer:{question}", citation_chunk_ids=self.citation_chunk_ids)


def test_reference_question_consumer_cannot_cite_outside_hits(tmp_path: Path) -> None:
    with _session() as db:
        seed = _seed_contract_materials(db, tmp_path)
        unselected_chunk_id = seed.history_chunks[0].id

        result = _reference_question_consumer(
            db,
            user_id=seed.user.id,
            course_id=seed.course.id,
            question="eigenvalue",
            scope=MaterialScope(include_all_parsed_materials=False, material_ids=[seed.math_material.id]),
            rag_index=seed.rag_index,
            model_provider=ReferenceQuestionModel(
                citation_chunk_ids=[seed.math_chunks[0].id, unselected_chunk_id, "fabricated-chunk"]
            ),
        )

        assert result["context"].chunks
        assert unselected_chunk_id not in result["allowed_citation_ids"]
        assert result["citation_chunk_ids"] == [seed.math_chunks[0].id]


def test_reference_generation_consumer_processes_all_selected_materials(tmp_path: Path) -> None:
    with _session() as db:
        seed = _seed_contract_materials(db, tmp_path)
        selected_material_ids = {seed.math_material.id, seed.history_material.id}

        result = _reference_generation_consumer(
            db,
            user_id=seed.user.id,
            course_id=seed.course.id,
            scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[seed.math_material.id, seed.history_material.id],
            ),
            expected_material_ids=selected_material_ids,
        )

        assert result.processed_material_ids == selected_material_ids
        assert set(result.value) == {"fact:math.txt", "fact:history.txt"}
        assert result.citation_chunk_ids.issubset({chunk.id for chunk in seed.math_chunks + seed.history_chunks})


def _reference_question_consumer(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    question: str,
    scope: MaterialScope,
    rag_index: FakeRagIndex,
    model_provider: ReferenceQuestionModel,
) -> dict[str, object]:
    context = retrieve_relevant_context(
        db,
        user_id=user_id,
        course_id=course_id,
        query=question,
        material_scope=scope,
        rag_index=rag_index,
        top_k=8,
    )
    allowed_citation_ids = {chunk.chunk_id for chunk in context.chunks}
    answer = model_provider.answer_question(question=question, context_chunks=context.chunks)
    citation_chunk_ids = [chunk_id for chunk_id in answer.citation_chunk_ids if chunk_id in allowed_citation_ids]
    return {
        "context": context,
        "allowed_citation_ids": allowed_citation_ids,
        "citation_chunk_ids": citation_chunk_ids,
    }


def _reference_generation_consumer(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    scope: MaterialScope,
    expected_material_ids: set[str],
) -> CoverageRunResult[list[str]]:
    batches = list(
        iter_material_context_batches(
            db,
            user_id=user_id,
            course_id=course_id,
            material_scope=scope,
            max_tokens=20,
        )
    )
    return run_material_coverage(
        batches=batches,
        expected_material_ids=expected_material_ids,
        map_batch=_reference_map,
        reduce_results=_reference_reduce,
    )


def _reference_map(batch: MaterialContextBatch) -> ReferenceBatchOutput:
    material_names = {
        chunk.material_id: chunk.material_name
        for chunk in batch.chunks
    }
    return ReferenceBatchOutput(
        facts=[f"fact:{material_name}" for material_name in material_names.values()],
        citation_chunk_ids=[chunk.chunk_id for chunk in batch.chunks],
    )


def _reference_reduce(items: list[ReferenceBatchOutput]) -> list[str]:
    return [fact for item in items for fact in item.facts]


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


def _seed_contract_materials(db: Session, tmp_path: Path) -> ContractSeed:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    rag_index = FakeRagIndex()
    math_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="math.txt",
        content="Eigenvalue and eigenvector notes\n\nMatrix trace",
        rag_index=rag_index,
    )
    history_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="history.txt",
        content="Archive source analysis\n\nTimeline source",
        rag_index=rag_index,
    )
    return ContractSeed(
        user=user,
        course=course,
        math_material=math_material,
        history_material=history_material,
        math_chunks=_material_chunks(db, math_material.id),
        history_chunks=_material_chunks(db, history_material.id),
        rag_index=rag_index,
    )


def _create_and_parse_material(
    db: Session,
    tmp_path: Path,
    *,
    user_id: str,
    course_id: str,
    filename: str,
    content: str,
    rag_index: FakeRagIndex,
) -> CourseMaterial:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        stream=BytesIO(content.encode("utf-8")),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
    )
    return parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )


def _material_chunks(db: Session, material_id: str) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material_id)
            .order_by(MaterialChunk.chunk_index.asc())
        ).scalars()
    )
