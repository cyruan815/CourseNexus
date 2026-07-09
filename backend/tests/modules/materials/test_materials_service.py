from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
import app.modules.materials.service as materials_service
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.schemas import MaterialLinkCreate
from app.modules.materials.service import (
    create_link_material,
    delete_material,
    get_material_detail,
    list_course_materials,
    upload_file_material,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


def test_materials_service_depends_on_file_storage_protocol_not_local_adapter() -> None:
    source = Path(materials_service.__file__).read_text(encoding="utf-8")

    assert "app.integrations.file_storage.local" not in source


def office_stream(member_name: str) -> BytesIO:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member_name, "<xml />")
    stream.seek(0)
    return stream


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


def test_upload_file_material_creates_uploaded_material(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.md",
        stream=BytesIO(b"# Intro"),
        content_type="application/octet-stream",
        storage=storage,
    )

    assert material.course_id == course.id
    assert material.user_id == user.id
    assert material.name == "notes.md"
    assert material.material_type == "markdown"
    assert material.source_type == "file"
    assert material.file_size == 7
    assert material.mime_type == "text/markdown"
    assert material.parse_status == "uploaded"
    assert material.file_url == f"{user.id}/{course.id}/{material.id}/notes.md"
    assert (tmp_path / material.file_url).read_text(encoding="utf-8") == "# Intro"


@pytest.mark.parametrize(
    ("filename", "stream", "material_type", "mime_type"),
    [
        ("slides.pdf", BytesIO(b"%PDF-1.7\n%%EOF"), "pdf", "application/pdf"),
        (
            "notes.docx",
            office_stream("word/document.xml"),
            "word",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "deck.pptx",
            office_stream("ppt/presentation.xml"),
            "ppt",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("diagram.png", BytesIO(b"\x89PNG\r\n\x1a\nrest"), "image", "image/png"),
        ("photo.jpeg", BytesIO(b"\xff\xd8\xff\xe0rest"), "image", "image/jpeg"),
    ],
)
def test_upload_file_material_accepts_complex_formats(
    db: Session,
    tmp_path,
    filename: str,
    stream: BytesIO,
    material_type: str,
    mime_type: str,
) -> None:
    user = register_user(db, UserCreate(username=f"alice_{material_type}_{filename}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename=filename,
        stream=stream,
        content_type="application/octet-stream",
        storage=storage,
    )

    assert material.material_type == material_type
    assert material.mime_type == mime_type
    assert material.parse_status == "uploaded"


def test_create_link_material_creates_url_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    material = create_link_material(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=MaterialLinkCreate(name="Course Site", source_url="https://example.com/course"),
    )

    assert material.material_type == "link"
    assert material.source_type == "url"
    assert material.source_url == "https://example.com/course"
    assert material.parse_status == "uploaded"


def test_list_and_detail_are_scoped_to_user(db: Session, tmp_path) -> None:
    alice = register_user(db, UserCreate(username="alice", password="password123"))
    bob = register_user(db, UserCreate(username="bob", password="password123"))
    alice_course = create_course(db, alice.id, CourseCreate(name="Linear Algebra"))
    bob_course = create_course(db, bob.id, CourseCreate(name="Databases"))
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    alice_material = upload_file_material(
        db,
        user_id=alice.id,
        course_id=alice_course.id,
        filename="alice.txt",
        stream=BytesIO(b"alice notes"),
        content_type="text/plain",
        storage=storage,
    )
    bob_material = upload_file_material(
        db,
        user_id=bob.id,
        course_id=bob_course.id,
        filename="bob.txt",
        stream=BytesIO(b"bob notes"),
        content_type="text/plain",
        storage=storage,
    )

    assert [material.id for material in list_course_materials(db, alice.id, alice_course.id)] == [alice_material.id]
    assert get_material_detail(db, alice.id, alice_material.id).id == alice_material.id

    with pytest.raises(CourseNexusError) as exc_info:
        get_material_detail(db, alice.id, bob_material.id)

    assert exc_info.value.code == "NOT_FOUND"


def test_delete_material_soft_deletes_and_hides_from_list(db: Session, tmp_path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.txt",
        stream=BytesIO(b"notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )

    deleted = delete_material(db, user.id, material.id)

    assert deleted.parse_status == "deleted"
    assert deleted.deleted_at is not None
    assert list_course_materials(db, user.id, course.id) == []
