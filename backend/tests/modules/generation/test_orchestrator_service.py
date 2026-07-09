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
from app.modules.course_qa.models import SourceCitation
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator
from app.modules.generation.orchestrator.contracts import GenerateContentRequest, GeneratorOutput
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.generation.orchestrator.service import generate_content
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


def registry_with(generator) -> GeneratorRegistry:
    registry = GeneratorRegistry()
    registry.register("outline", generator)
    return registry


def test_generate_content_writes_success_content_and_citations(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline", material_scope=MaterialScope()),
        registry=registry_with(PlaceholderGenerator(content_type="outline")),
    )

    assert content.content_type == "outline"
    assert content.generation_status == "success"
    citations = list(db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars())
    assert len(citations) == 1
    assert citations[0].material_name == "notes.md"
    assert content.title == "Outline"
    assert content.content_json == {"items": ["Alpha"]}


def test_generate_content_requires_parsed_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(PlaceholderGenerator(content_type="outline")),
        )

    assert exc_info.value.code == "NO_PARSED_MATERIAL"


class FailingGenerator:
    def generate(self, *, context, parameters):
        raise CourseNexusError(code="GENERATION_FAILED", message="生成失败")


class EmptyGenerator:
    def generate(self, *, context, parameters):
        return GeneratorOutput(title="Empty", content="", content_json={}, citation_chunk_ids=[])


def test_generate_content_writes_failed_content_on_generator_failure(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(FailingGenerator()),
    )

    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_FAILED"


def test_generate_content_requires_real_citations(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(EmptyGenerator()),
    )

    assert content.generation_status == "success"
