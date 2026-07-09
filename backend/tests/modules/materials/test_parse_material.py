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
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import MaterialChunk
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


def create_uploaded_material(db: Session, tmp_path: Path, filename: str = "notes.md"):
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename=filename,
        stream=BytesIO(b"# Intro\nAlpha\n"),
        content_type="text/markdown",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )
    return user, course, material


def material_chunks(db: Session, material_id: str) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material_id)
            .order_by(MaterialChunk.chunk_index)
        ).scalars()
    )


def test_parse_material_writes_chunks_and_marks_parsed(db: Session, tmp_path: Path) -> None:
    user, course, material = create_uploaded_material(db, tmp_path)
    rag_index = FakeRagIndex()

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    chunks = material_chunks(db, material.id)
    assert parsed.parse_status == "parsed"
    assert parsed.parse_error is None
    assert len(chunks) == 1
    assert chunks[0].course_id == course.id
    assert chunks[0].chunk_index == 0
    assert chunks[0].heading == "Intro"
    assert chunks[0].content_text == "Alpha"
    assert chunks[0].id == f"chk_{material.id.removeprefix('mat_')}_000000"
    assert chunks[0].embedding_id == chunks[0].id
    assert {record.material_id for record in rag_index.records.values()} == {material.id}
    assert {record.course_id for record in rag_index.records.values()} == {course.id}
    assert {record.user_id for record in rag_index.records.values()} == {user.id}


def test_parse_material_failure_marks_parse_failed(db: Session, tmp_path: Path) -> None:
    class FailingParser:
        def parse(self, file_path: Path):
            raise CourseNexusError(code="PARSE_FAILED", message="解析失败")

    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=FailingParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "PARSE_FAILED"
    assert material_chunks(db, material.id) == []


def test_reparse_material_replaces_old_chunks(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    parser = PlainTextParser()
    rag_index = FakeRagIndex()
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )
    (tmp_path / material.file_url).write_text("First\n\nSecond\n", encoding="utf-8")

    reparsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=parser,
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    chunks = material_chunks(db, material.id)
    assert reparsed.parse_status == "parsed"
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert [chunk.content_text for chunk in chunks] == ["First", "Second"]
    assert set(rag_index.records) == {
        f"chk_{material.id.removeprefix('mat_')}_000000",
        f"chk_{material.id.removeprefix('mat_')}_000001",
    }


def test_deleted_material_cannot_be_parsed(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)
    delete_material(db, user.id, material.id, rag_index=FakeRagIndex())

    with pytest.raises(CourseNexusError) as exc_info:
        parse_material(
            db,
            user_id=user.id,
            material_id=material.id,
            parser=PlainTextParser(),
            rag_index=FakeRagIndex(),
            storage_root=tmp_path,
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_parse_indexes_every_saved_chunk(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user, course, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parsed"
    assert {record.material_id for record in rag_index.records.values()} == {material.id}
    assert {record.course_id for record in rag_index.records.values()} == {course.id}


def test_parse_material_index_failure_marks_failed_and_clears_chunks(db: Session, tmp_path: Path) -> None:
    class FailingRagIndex(FakeRagIndex):
        def index_chunks(self, chunks):
            super().index_chunks(chunks)
            raise CourseNexusError(code="INDEXING_FAILED", message="索引失败", status_code=502)

    rag_index = FailingRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "INDEXING_FAILED"
    assert material_chunks(db, material.id) == []
    assert rag_index.records == {}


def test_parse_material_index_failure_still_marks_failed_when_cleanup_raises(db: Session, tmp_path: Path) -> None:
    class FailingCleanupRagIndex(FakeRagIndex):
        def index_chunks(self, chunks):
            super().index_chunks(chunks)
            raise CourseNexusError(code="INDEXING_FAILED", message="索引失败", status_code=502)

        def delete_material(self, material_id: str) -> None:
            raise CourseNexusError(code="INDEXING_FAILED", message="删除失败", status_code=502)

    user, _, material = create_uploaded_material(db, tmp_path)

    parsed = parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=FailingCleanupRagIndex(),
        storage_root=tmp_path,
    )

    assert parsed.parse_status == "parse_failed"
    assert parsed.parse_error == "INDEXING_FAILED"
    assert material_chunks(db, material.id) == []


def test_delete_material_removes_vectors(db: Session, tmp_path: Path) -> None:
    rag_index = FakeRagIndex()
    user, _, material = create_uploaded_material(db, tmp_path)
    parse_material(
        db,
        user_id=user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    deleted = delete_material(db, user.id, material.id, rag_index=rag_index)

    assert deleted.parse_status == "deleted"
    assert rag_index.records == {}


def test_delete_material_requires_rag_index(db: Session, tmp_path: Path) -> None:
    user, _, material = create_uploaded_material(db, tmp_path)

    with pytest.raises(TypeError):
        delete_material(db, user.id, material.id)
