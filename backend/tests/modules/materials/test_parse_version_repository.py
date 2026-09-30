from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import MaterialChunk, MaterialParseVersion
from app.modules.materials.repository import (
    delete_material_chunks_for_parse_version_in_session,
    get_building_parse_version,
    get_parse_version_for_material,
    list_material_chunks_for_parse_version,
    list_parse_versions_for_material,
    save_parse_version,
)
from app.modules.materials.service import upload_file_material
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


def _material(db: Session, tmp_path):
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    return upload_file_material(
        db,
        user_id=user.id,
        course_id=course.id,
        filename="notes.txt",
        stream=BytesIO(b"notes"),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024),
    )


def _version(material, version_id: str, status: str = "building") -> MaterialParseVersion:
    return MaterialParseVersion(
        id=version_id,
        material_id=material.id,
        course_id=material.course_id,
        user_id=material.user_id,
        status=status,
    )


def test_repository_reads_versions_and_candidate_chunks(db: Session, tmp_path) -> None:
    material = _material(db, tmp_path)
    version = save_parse_version(db, _version(material, "mpv_1"))
    chunk = MaterialChunk(
        id="chk_1",
        material_id=material.id,
        parse_version_id=version.id,
        course_id=material.course_id,
        chunk_index=0,
        content_text="candidate",
    )
    db.add(chunk)
    db.commit()

    assert get_building_parse_version(db, material.id).id == version.id
    assert get_parse_version_for_material(
        db,
        material_id=material.id,
        parse_version_id=version.id,
    ).id == version.id
    assert [item.id for item in list_parse_versions_for_material(db, material.id)] == [version.id]
    assert [item.id for item in list_material_chunks_for_parse_version(db, version.id)] == [chunk.id]

    delete_material_chunks_for_parse_version_in_session(db, version.id)
    db.commit()

    assert list_material_chunks_for_parse_version(db, version.id) == []


def test_database_rejects_second_building_version(db: Session, tmp_path) -> None:
    material = _material(db, tmp_path)
    save_parse_version(db, _version(material, "mpv_1"))

    with pytest.raises(IntegrityError):
        save_parse_version(db, _version(material, "mpv_2"))

    db.rollback()
