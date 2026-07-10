from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.base import ModelAnswer
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.course_qa.models import Message, SourceCitation
from app.modules.course_qa.schemas import CourseQuestionCreate
from app.modules.course_qa.service import ask_course_question
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import ContextChunk, MaterialScope
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@pytest.fixture()
def db() -> Generator[Session, None, None]:
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


class RecordingModelProvider:
    def __init__(self, *, citation_chunk_ids: list[str]) -> None:
        self.citation_chunk_ids = citation_chunk_ids
        self.context_chunks: list[ContextChunk] = []
        self.call_count = 0

    def answer_question(self, *, question: str, context_chunks: list[ContextChunk]) -> ModelAnswer:
        self.call_count += 1
        self.context_chunks = context_chunks
        return ModelAnswer(answer_text="retrieved answer", citation_chunk_ids=self.citation_chunk_ids)


def create_parsed_material(
    db: Session,
    tmp_path: Path,
    user_id: str,
    course_id: str,
    *,
    content: bytes = b"# Intro\nAlpha\n",
    rag_index: FakeRagIndex | None = None,
) -> CourseMaterial:
    rag_index = rag_index or FakeRagIndex()
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename="notes.md",
        stream=BytesIO(content),
        content_type="text/markdown",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    return parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )


def messages(db: Session) -> list[Message]:
    return list(db.execute(select(Message).order_by(Message.created_at)).scalars())


def citations(db: Session) -> list[SourceCitation]:
    return list(db.execute(select(SourceCitation).order_by(SourceCitation.sort_order)).scalars())


def material_chunks(db: Session, material_id: str) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material_id)
            .order_by(MaterialChunk.chunk_index)
        ).scalars()
    )


def test_ask_course_question_creates_messages_and_citations(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id, rag_index=rag_index)

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="What is Alpha?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
        rag_index=rag_index,
    )

    saved_messages = messages(db)
    saved_citations = citations(db)
    assert answer.answer_type == "grounded"
    assert answer.conversation_id
    assert [message.role for message in saved_messages] == ["user", "assistant"]
    assert saved_messages[1].answer_type == "grounded"
    assert saved_citations[0].message_id == saved_messages[1].id
    assert saved_citations[0].material_name == "notes.md"
    assert saved_citations[0].chunk_id is not None


def test_ask_course_question_uses_retrieved_chunks_for_model_and_citations(
    db: Session,
    tmp_path: Path,
) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        content=b"# History\nindustrial revolution\n\n# Algebra\nmatrix eigenvalue diagonalization\n",
        rag_index=rag_index,
    )
    _, eigen_chunk = material_chunks(db, material.id)
    model_provider = RecordingModelProvider(citation_chunk_ids=["not-a-hit", eigen_chunk.id])

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="How does eigenvalue work?", material_scope=MaterialScope()),
        model_provider=model_provider,
        rag_index=rag_index,
    )

    assert [chunk.chunk_id for chunk in model_provider.context_chunks] == [eigen_chunk.id]
    assert [citation.chunk_id for citation in answer.source_citations] == [eigen_chunk.id]


def test_ask_course_question_without_retrieval_hits_returns_no_source_without_model(
    db: Session,
    tmp_path: Path,
) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        content=b"# History\nindustrial revolution\n",
        rag_index=rag_index,
    )
    model_provider = RecordingModelProvider(citation_chunk_ids=[])

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="matrix eigenvalue", material_scope=MaterialScope()),
        model_provider=model_provider,
        rag_index=rag_index,
    )

    assert answer.answer_type == "no_source"
    assert answer.source_citations == []
    assert model_provider.call_count == 0
    assert citations(db) == []


def test_ask_course_question_with_selected_unparsed_material_returns_no_source_without_model(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="uploaded.txt",
        stream=BytesIO(b"not parsed yet"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    model_provider = RecordingModelProvider(citation_chunk_ids=[])

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(
            question="What is inside?",
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[material.id],
            ),
        ),
        model_provider=model_provider,
        rag_index=FakeRagIndex(),
    )

    assert answer.answer_type == "no_source"
    assert answer.source_citations == []
    assert model_provider.call_count == 0
    assert citations(db) == []


def test_ask_course_question_does_not_save_uncited_fallback_citation(
    db: Session,
    tmp_path: Path,
) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        content=b"# Algebra\nmatrix eigenvalue diagonalization\n",
        rag_index=rag_index,
    )
    model_provider = RecordingModelProvider(citation_chunk_ids=["not-a-retrieved-chunk"])

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="eigenvalue", material_scope=MaterialScope()),
        model_provider=model_provider,
        rag_index=rag_index,
    )

    assert answer.answer_type == "grounded"
    assert answer.source_citations == []
    assert citations(db) == []


def test_ask_course_question_without_parsed_material_returns_no_source(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="What is Alpha?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
        rag_index=FakeRagIndex(),
    )

    assert answer.answer_type == "no_source"
    assert answer.source_citations == []
    assert citations(db) == []
    assert messages(db)[1].answer_type == "no_source"


def test_ask_course_question_reuses_conversation(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id, rag_index=rag_index)
    first_answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="First?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
        rag_index=rag_index,
    )

    second_answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(
            conversation_id=first_answer.conversation_id,
            question="Second?",
            material_scope=MaterialScope(),
        ),
        model_provider=MockModelProvider(),
        rag_index=rag_index,
    )

    assert second_answer.conversation_id == first_answer.conversation_id
    assert len(messages(db)) == 4


def test_cross_course_conversation_reuse_is_rejected(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user = register_user(db, UserCreate(username="alice", password="password123"))
    first_course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    second_course = create_course(db, user.id, CourseCreate(name="Databases"))
    create_parsed_material(db, tmp_path, user.id, first_course.id, rag_index=rag_index)
    first_answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=first_course.id,
        payload=CourseQuestionCreate(question="First?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
        rag_index=rag_index,
    )

    with pytest.raises(CourseNexusError) as exc_info:
        ask_course_question(
            db,
            user_id=user.id,
            course_id=second_course.id,
            payload=CourseQuestionCreate(
                conversation_id=first_answer.conversation_id,
                question="Wrong course?",
                material_scope=MaterialScope(),
            ),
            model_provider=MockModelProvider(),
            rag_index=rag_index,
        )

    assert exc_info.value.code == "NOT_FOUND"
