from __future__ import annotations

from collections.abc import Callable, Generator as IteratorGenerator
from inspect import Parameter, signature
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import CourseNexusError
from app.db.base import Base
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator
from app.modules.generation.orchestrator.contracts import (
    GenerateContentRequest,
    Generator,
    GeneratorOutput,
)
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.generation.orchestrator.service import generate_content
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope
from app.modules.materials.models import CourseMaterial
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


@pytest.fixture()
def db() -> IteratorGenerator[Session, None, None]:
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


def create_parsed_material(
    db: Session,
    tmp_path: Path,
    user_id: str,
    course_id: str,
    *,
    filename: str = "notes.md",
    content: str = "# Intro\nAlpha\n",
) -> CourseMaterial:
    material = upload_file_material(
        db,
        user_id=user_id,
        course_id=course_id,
        filename=filename,
        stream=BytesIO(content.encode("utf-8")),
        content_type="text/markdown",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
    )
    return parse_material(
        db,
        user_id=user_id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=FakeRagIndex(),
        storage_root=tmp_path,
    )


def registry_with(factory: Callable[[ModelProvider], Generator]) -> GeneratorRegistry:
    registry = GeneratorRegistry()
    registry.register("outline", factory)
    return registry


def placeholder_factory(model_provider: ModelProvider) -> Generator:
    return PlaceholderGenerator(content_type="outline", model_provider=model_provider)


def test_generate_content_freezes_injected_provider_and_batch_budget_signature() -> None:
    generate_signature = signature(generate_content)

    assert tuple(generate_signature.parameters) == (
        "db",
        "user_id",
        "course_id",
        "payload",
        "registry",
        "model_provider",
        "max_batch_tokens",
    )
    assert generate_signature.parameters["db"].kind is Parameter.POSITIONAL_OR_KEYWORD
    for name in tuple(generate_signature.parameters)[1:]:
        assert generate_signature.parameters[name].kind is Parameter.KEYWORD_ONLY


def test_generate_content_rejects_unsupported_type_before_loading_materials(db: Session) -> None:
    user = register_user(db, UserCreate(username="unsupported", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="unknown"),
            registry=GeneratorRegistry(),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.status_code == 422


def test_generate_content_rejects_inaccessible_courses_before_generator_factory(db: Session) -> None:
    owner = register_user(db, UserCreate(username="course-owner", password="password123"))
    other_user = register_user(db, UserCreate(username="other-user", password="password123"))
    course = create_course(db, owner.id, CourseCreate(name="Linear Algebra"))
    factory_calls: list[ModelProvider] = []

    def recording_factory(model_provider: ModelProvider) -> Generator:
        factory_calls.append(model_provider)
        return PlaceholderGenerator(content_type="outline", model_provider=model_provider)

    for inaccessible_course_id in (course.id, "crs_missing"):
        with pytest.raises(CourseNexusError) as exc_info:
            generate_content(
                db,
                user_id=other_user.id,
                course_id=inaccessible_course_id,
                payload=GenerateContentRequest(content_type="outline"),
                registry=registry_with(recording_factory),
                model_provider=MockModelProvider(),
                max_batch_tokens=100,
            )

        assert exc_info.value.code == "NOT_FOUND"
        assert exc_info.value.status_code == 404

    assert factory_calls == []


def test_generate_content_writes_success_content_without_task5_citations(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline", material_scope=MaterialScope()),
        registry=registry_with(placeholder_factory),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert content.content_type == "outline"
    assert content.generation_status == "success"
    citations = list(
        db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars()
    )
    assert citations == []
    assert content.title == "Outline"
    assert content.content == "Alpha"
    assert content.content_json["items"][0]["text"] == "Alpha"


class RecordingGenerator:
    content_type = "outline"

    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider
        self.batches: tuple[MaterialContextBatch, ...] = ()
        self.expected_material_ids: frozenset[str] = frozenset()

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        self.batches = batches
        self.expected_material_ids = expected_material_ids
        first_chunk = batches[0].chunks[0]
        return GeneratorOutput(
            title="Recorded",
            content=first_chunk.content_text,
            content_json={"items": []},
            item_citation_chunk_ids={"recorded-item": [first_chunk.chunk_id]},
        )


def test_generate_content_injects_provider_and_delivers_all_material_batches(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="batch-user", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    first_material = create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        filename="first.txt",
        content="First material section one\n\nFirst material section two",
    )
    second_material = create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        filename="second.txt",
        content="Second material section one\n\nSecond material section two",
    )
    model_provider = MockModelProvider()
    created_generators: list[RecordingGenerator] = []

    def recording_factory(received_provider: ModelProvider) -> Generator:
        generator = RecordingGenerator(received_provider)
        created_generators.append(generator)
        return generator

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(recording_factory),
        model_provider=model_provider,
        max_batch_tokens=5,
    )

    assert content.generation_status == "success"
    assert len(created_generators) == 1
    generator = created_generators[0]
    assert generator.model_provider is model_provider
    assert len(generator.batches) == 4
    assert sum(len(batch.chunks) for batch in generator.batches) == 4
    assert generator.expected_material_ids == frozenset({first_material.id, second_material.id})
    delivered_material_ids = frozenset(
        material_id for batch in generator.batches for material_id in batch.material_ids
    )
    assert delivered_material_ids == generator.expected_material_ids


def test_generate_content_requires_parsed_material(db: Session) -> None:
    user = register_user(db, UserCreate(username="no-material", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))

    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(placeholder_factory),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )

    assert exc_info.value.code == "NO_PARSED_MATERIAL"
    assert exc_info.value.status_code == 400


class FailingGenerator:
    content_type = "outline"

    def generate(self, *, batches, expected_material_ids, parameters):
        raise CourseNexusError(code="GENERATION_FAILED", message="Generation failed")


class OpaqueCitationMetadataGenerator:
    content_type = "outline"

    def generate(self, *, batches, expected_material_ids, parameters):
        first_chunk = batches[0].chunks[0]
        return GeneratorOutput(
            title="Opaque citations",
            content="",
            content_json={},
            item_citation_chunk_ids={"item-1": [first_chunk.chunk_id]},
        )


def test_generate_content_writes_failed_content_on_generator_failure(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="failure", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(lambda provider: FailingGenerator()),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_FAILED"


def test_generate_content_does_not_interpret_item_citation_metadata(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="empty", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(lambda provider: OpaqueCitationMetadataGenerator()),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert content.generation_status == "success"
    citations = list(
        db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars()
    )
    assert citations == []
