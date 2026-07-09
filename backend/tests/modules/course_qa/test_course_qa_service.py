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
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.course_qa.models import Message, SourceCitation
from app.modules.course_qa.schemas import CourseQuestionCreate
from app.modules.course_qa.service import ask_course_question
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import MaterialScope
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


def create_parsed_material(db: Session, tmp_path: Path, user_id: str, course_id: str) -> None:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename="notes.md",
        stream=BytesIO(b"# Intro\nAlpha\n"),
        content_type="text/markdown",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )


def messages(db: Session) -> list[Message]:
    return list(db.execute(select(Message).order_by(Message.created_at)).scalars())


def citations(db: Session) -> list[SourceCitation]:
    return list(db.execute(select(SourceCitation).order_by(SourceCitation.sort_order)).scalars())


def test_ask_course_question_creates_messages_and_citations(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="What is Alpha?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
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


def test_ask_course_question_without_parsed_material_returns_no_source(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="What is Alpha?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
    )

    assert answer.answer_type == "no_source"
    assert answer.source_citations == []
    assert citations(db) == []
    assert messages(db)[1].answer_type == "no_source"


def test_ask_course_question_reuses_conversation(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)
    first_answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=CourseQuestionCreate(question="First?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
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
    )

    assert second_answer.conversation_id == first_answer.conversation_id
    assert len(messages(db)) == 4


def test_cross_course_conversation_reuse_is_rejected(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    first_course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    second_course = create_course(db, user.id, CourseCreate(name="Databases"))
    create_parsed_material(db, tmp_path, user.id, first_course.id)
    first_answer = ask_course_question(
        db,
        user_id=user.id,
        course_id=first_course.id,
        payload=CourseQuestionCreate(question="First?", material_scope=MaterialScope()),
        model_provider=MockModelProvider(),
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
        )

    assert exc_info.value.code == "NOT_FOUND"
