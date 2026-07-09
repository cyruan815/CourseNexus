from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@dataclass
class MaterialContextSeed:
    user: User
    course: Course
    other_user: User
    other_course: Course
    math_material: CourseMaterial
    history_material: CourseMaterial
    folder_material: CourseMaterial
    empty_material: CourseMaterial
    folder: MaterialFolder
    math_chunks: list[MaterialChunk]
    history_chunks: list[MaterialChunk]
    folder_chunks: list[MaterialChunk]
    rag_index: FakeRagIndex


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


@pytest.fixture()
def context_seed(db: Session, tmp_path: Path) -> MaterialContextSeed:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    other_user = register_user(db, UserCreate(username="bob", password="password123"))
    other_course = create_course(db, other_user.id, CourseCreate(name="Databases"))
    folder = MaterialFolder(id="fld_week_1", user_id=user.id, course_id=course.id, name="Week 1")
    db.add(folder)
    db.commit()

    rag_index = FakeRagIndex()
    math_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="math.txt",
        content="Eigenvalue eigenvector decomposition\n\nMatrix trace determinant",
        rag_index=rag_index,
    )
    history_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="history.txt",
        content="Archive source analysis\n\nTimeline source notes",
        rag_index=rag_index,
    )
    folder_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="folder.txt",
        content="Folder eigenvalue appendix",
        rag_index=rag_index,
        folder_id=folder.id,
    )
    empty_material = _create_and_parse_material(
        db,
        tmp_path,
        user_id=user.id,
        course_id=course.id,
        filename="empty.txt",
        content="",
        rag_index=rag_index,
    )

    return MaterialContextSeed(
        user=user,
        course=course,
        other_user=other_user,
        other_course=other_course,
        math_material=math_material,
        history_material=history_material,
        folder_material=folder_material,
        empty_material=empty_material,
        folder=folder,
        math_chunks=_material_chunks(db, math_material.id),
        history_chunks=_material_chunks(db, history_material.id),
        folder_chunks=_material_chunks(db, folder_material.id),
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
    folder_id: str | None = None,
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
    if folder_id is not None:
        material.folder_id = folder_id
        db.add(material)
        db.commit()
        db.refresh(material)

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
