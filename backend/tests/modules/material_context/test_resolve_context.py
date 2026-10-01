from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.material_context.schemas import MaterialScope
from app.modules.material_context.service import resolve_context
from app.modules.materials.models import CourseMaterial
from app.modules.materials.service import delete_material, parse_material, upload_file_material
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


def create_material(
    db: Session,
    tmp_path: Path,
    *,
    user_id: str,
    course_id: str,
    filename: str,
    content: bytes,
):
    return upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        stream=BytesIO(content),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )


def parse_uploaded_material(db: Session, tmp_path: Path, user_id: str, material_id: str):
    return parse_material(
        db,
        user_id=user_id,
        material_id=material_id,
        parser=PlainTextParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )


def test_default_scope_returns_all_parsed_chunks_only(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    parsed = create_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="parsed.txt",
        content=b"parsed content",
    )
    uploaded = create_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="uploaded.txt",
        content=b"uploaded content",
    )
    deleted = create_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="deleted.txt",
        content=b"deleted content",
    )
    parse_uploaded_material(db, tmp_path, user.id, parsed.id)
    delete_material(
        db,
        user.id,
        deleted.id,
        rag_index=FakeRagIndex(),
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    result = resolve_context(db, user.id, course.id, MaterialScope())

    assert result.no_parsed_material is False
    assert [chunk.material_id for chunk in result.chunks] == [parsed.id]
    assert result.chunks[0].material_name == "parsed.txt"
    assert result.chunks[0].content_text == "parsed content"
    assert uploaded.id not in [chunk.material_id for chunk in result.chunks]


def test_legacy_url_material_never_enters_resolved_context(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    parsed = create_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="parsed.txt",
        content=b"parsed content",
    )
    parse_uploaded_material(db, tmp_path, user.id, parsed.id)
    legacy_url = CourseMaterial(
        id="mat_legacy_url",
        course_id=course.id,
        user_id=user.id,
        name="reference",
        material_type="link",
        source_type="url",
        source_url="https://example.com/reference",
        parse_status="uploaded",
    )
    db.add(legacy_url)
    db.commit()

    result = resolve_context(db, user.id, course.id, MaterialScope())

    assert result.no_parsed_material is False
    assert [chunk.material_id for chunk in result.chunks] == [parsed.id]

    scoped = resolve_context(
        db,
        user.id,
        course.id,
        MaterialScope(include_all_parsed_materials=False, material_ids=[legacy_url.id]),
    )
    assert scoped.no_parsed_material is True
    assert scoped.chunks == []


def test_material_ids_scope_returns_requested_parsed_material(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    first = create_material(db, tmp_path, user_id=user.id, course_id=course.id, filename="first.txt", content=b"first")
    second = create_material(db, tmp_path, user_id=user.id, course_id=course.id, filename="second.txt", content=b"second")
    parse_uploaded_material(db, tmp_path, user.id, first.id)
    parse_uploaded_material(db, tmp_path, user.id, second.id)

    result = resolve_context(
        db,
        user.id,
        course.id,
        MaterialScope(include_all_parsed_materials=False, material_ids=[second.id]),
    )

    assert [chunk.material_id for chunk in result.chunks] == [second.id]
    assert result.no_parsed_material is False


def test_material_scope_rejects_folder_selection() -> None:
    with pytest.raises(ValidationError):
        MaterialScope(include_all_parsed_materials=False, folder_ids=["fld_1"])


def test_cross_user_material_id_is_rejected(db: Session, tmp_path: Path) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))
    bob_material = create_material(
        db,
        tmp_path,
        user_id=bob.id,
        course_id=bob_course.id,
        filename="bob.txt",
        content=b"bob",
    )
    parse_uploaded_material(db, tmp_path, bob.id, bob_material.id)

    with pytest.raises(CourseNexusError) as exc_info:
        resolve_context(
            db,
            alice.id,
            alice_course.id,
            MaterialScope(include_all_parsed_materials=False, material_ids=[bob_material.id]),
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_no_parsed_material_true_when_scope_has_no_available_chunks(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_material(db, tmp_path, user_id=user.id, course_id=course.id, filename="uploaded.txt", content=b"uploaded")

    result = resolve_context(db, user.id, course.id, MaterialScope())

    assert result.chunks == []
    assert result.no_parsed_material is True
