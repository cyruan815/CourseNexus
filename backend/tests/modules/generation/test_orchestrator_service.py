from __future__ import annotations

import logging
from collections.abc import Callable
from inspect import Parameter, signature
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
import app.db.models  # noqa: F401
from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.course_qa.models import SourceCitation
from app.modules.courses.schemas import CourseCreate
from app.modules.courses.service import create_course
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator
from app.modules.generation.orchestrator import service as orchestrator_service
from app.modules.generation.orchestrator.contracts import (
    GenerateContentRequest,
    Generator,
    GeneratorOutput,
)
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.generation.orchestrator.service import generate_content
from app.modules.material_context.schemas import MaterialContextBatch, MaterialScope
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.service import parse_material, upload_file_material
from app.modules.users.schemas import UserCreate
from app.modules.users.service import register_user


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


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


def test_generate_content_writes_success_content_with_bound_citation(
    db: Session,
    tmp_path: Path,
    caplog,
) -> None:
    logger = capture_course_logs(caplog)
    user = register_user(db, UserCreate(username="alice", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = create_parsed_material(db, tmp_path, user.id, course.id)
    chunk = _material_chunks(db, material.id)[0]
    chunk.page = "1"
    db.commit()

    try:
        content = generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline", material_scope=MaterialScope()),
            registry=registry_with(placeholder_factory),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert content.content_type == "outline"
    assert content.generation_status == "success"
    assert content.title == "Outline"
    assert content.content == "Alpha"
    assert content.content_json["items"][0]["text"] == "Alpha"
    citations = list(
        db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars()
    )
    assert len(citations) == 1
    assert content.content_json["items"][0]["source_citation_ids"] == [citations[0].id]
    record = next(record for record in caplog.records if record.name.endswith("generation.content"))
    assert "内容生成成功" in record.getMessage()
    assert "content_type=outline" in record.getMessage()
    assert "citations=1" in record.getMessage()


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
    assert list(db.execute(select(AIGeneratedContent)).scalars()) == []


def test_generate_content_persists_real_material_coverage_failure(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="coverage-gap", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = create_parsed_material(db, tmp_path, user.id, course.id)
    db.execute(delete(MaterialChunk).where(MaterialChunk.material_id == material.id))
    db.commit()
    scope = MaterialScope(
        include_all_parsed_materials=False,
        material_ids=[material.id],
    )
    generator_calls = 0

    class NeverCalledGenerator:
        content_type = "outline"

        def generate(self, *, batches, expected_material_ids, parameters):
            nonlocal generator_calls
            generator_calls += 1
            raise AssertionError("coverage failure must happen before generation")

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline", material_scope=scope),
        registry=registry_with(lambda provider: NeverCalledGenerator()),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert generator_calls == 0
    assert content.generation_status == "failed"
    assert content.error_code == "MATERIAL_COVERAGE_INCOMPLETE"
    assert content.content is None
    assert content.content_json is None
    assert content.material_scope_json == scope.model_dump(mode="json")
    assert list(db.execute(select(AIGeneratedContent)).scalars()) == [content]
    assert list(db.execute(select(SourceCitation)).scalars()) == []


class ErrorGenerator:
    content_type = "outline"

    def __init__(self, code: str) -> None:
        self.code = code

    def generate(self, *, batches, expected_material_ids, parameters):
        raise CourseNexusError(code=self.code, message="Generation failed")


class UnexpectedErrorGenerator:
    content_type = "outline"

    def generate(self, *, batches, expected_material_ids, parameters):
        raise RuntimeError("provider exploded")


@pytest.mark.parametrize(
    "error_code",
    ["GENERATION_FAILED", "GENERATION_SCHEMA_INVALID", "MATERIAL_COVERAGE_INCOMPLETE"],
)
def test_generate_content_persists_stable_generator_failure(
    db: Session,
    tmp_path: Path,
    error_code: str,
) -> None:
    user = register_user(db, UserCreate(username=f"failure-{error_code.lower()}", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)
    scope = MaterialScope(include_all_parsed_materials=True, material_ids=[])

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline", material_scope=scope),
        registry=registry_with(lambda provider: ErrorGenerator(error_code)),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert content.generation_status == "failed"
    assert content.error_code == error_code
    assert content.title == "Outline"
    assert content.content is None
    assert content.content_json is None
    assert content.material_scope_json == scope.model_dump(mode="json")
    assert list(
        db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars()
    ) == []
    assert len(list(db.execute(select(AIGeneratedContent)).scalars())) == 1


def test_generate_content_reraises_generator_validation_error_without_record(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="validation-error", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(lambda provider: ErrorGenerator("VALIDATION_ERROR")),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert list(db.execute(select(AIGeneratedContent)).scalars()) == []


def test_generate_content_maps_unexpected_generator_exception_to_failed_record(
    db: Session,
    tmp_path: Path,
    caplog,
) -> None:
    logger = capture_course_logs(caplog)
    user = register_user(db, UserCreate(username="unexpected-error", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    try:
        content = generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(lambda provider: UnexpectedErrorGenerator()),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )
    finally:
        logger.removeHandler(caplog.handler)

    assert content.generation_status == "failed"
    assert content.error_code == "GENERATION_FAILED"
    assert content.content is None
    assert content.content_json is None
    record = next(record for record in caplog.records if record.name.endswith("generation.content"))
    assert record.levelno == logging.ERROR
    assert "内容生成失败" in record.getMessage()
    assert "code=GENERATION_FAILED" in record.getMessage()
    assert isinstance(record.exc_info[1], RuntimeError)


def _material_chunks(db: Session, material_id: str) -> list[MaterialChunk]:
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id == material_id)
            .order_by(MaterialChunk.chunk_index)
        ).scalars()
    )


class CitationGenerator:
    content_type = "outline"

    def __init__(self, output_builder: Callable[[tuple[MaterialContextBatch, ...]], GeneratorOutput]) -> None:
        self.output_builder = output_builder

    def generate(self, *, batches, expected_material_ids, parameters):
        return self.output_builder(batches)


def test_generate_content_filters_binds_and_orders_real_item_citations(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="citation-binding", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    selected_material = create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        filename="selected.txt",
        content=f"{'A' * 550}\n\n{'B' * 40}",
    )
    outside_material = create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        filename="outside.txt",
        content="Outside material",
    )
    selected_chunks = _material_chunks(db, selected_material.id)
    outside_chunk = _material_chunks(db, outside_material.id)[0]
    selected_chunks[0].page = "p-10"
    selected_chunks[0].page_index = 9
    selected_chunks[1].page = "p-20"
    selected_chunks[1].page_index = 19
    db.commit()

    def build_output(batches: tuple[MaterialContextBatch, ...]) -> GeneratorOutput:
        delivered = [chunk for batch in batches for chunk in batch.chunks]
        first_chunk, second_chunk = delivered
        return GeneratorOutput(
            title="Bound citations",
            content="Rendered content",
            content_json={
                "sections": [
                    {
                        "id": "item-a",
                        "children": [{"id": "item-b", "source_citation_ids": ["stale"]}],
                    }
                ]
            },
            item_citation_chunk_ids={
                "item-a": [
                    second_chunk.chunk_id,
                    "fabricated-chunk",
                    second_chunk.chunk_id,
                    outside_chunk.id,
                    first_chunk.chunk_id,
                ],
                "item-b": [second_chunk.chunk_id],
                "removed-item": [first_chunk.chunk_id],
            },
        )

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(
            content_type="outline",
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[selected_material.id],
            ),
        ),
        registry=registry_with(lambda provider: CitationGenerator(build_output)),
        model_provider=MockModelProvider(),
        max_batch_tokens=1000,
    )

    citations = list(
        db.execute(
            select(SourceCitation)
            .where(SourceCitation.generated_content_id == content.id)
            .order_by(SourceCitation.sort_order)
        ).scalars()
    )
    assert [citation.chunk_id for citation in citations] == [chunk.id for chunk in selected_chunks]
    assert [citation.sort_order for citation in citations] == [1, 2]
    assert [citation.material_id for citation in citations] == [selected_material.id, selected_material.id]
    assert [citation.material_name for citation in citations] == [selected_material.name, selected_material.name]
    assert [(citation.page, citation.page_index) for citation in citations] == [("p-10", 9), ("p-20", 19)]
    assert [citation.hit_text for citation in citations] == ["A" * 500, "B" * 40]

    item_a = content.content_json["sections"][0]
    item_b = item_a["children"][0]
    citation_id_by_chunk_id = {citation.chunk_id: citation.id for citation in citations}
    assert item_a["source_citation_ids"] == [
        citation_id_by_chunk_id[selected_chunks[1].id],
        citation_id_by_chunk_id[selected_chunks[0].id],
    ]
    assert item_b["source_citation_ids"] == [citation_id_by_chunk_id[selected_chunks[1].id]]
    assert len(citations) == 2


def test_generate_content_keeps_empty_binding_without_fallback(db: Session, tmp_path: Path) -> None:
    user = register_user(db, UserCreate(username="empty-binding", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    def build_output(batches: tuple[MaterialContextBatch, ...]) -> GeneratorOutput:
        return GeneratorOutput(
            title="No valid citations",
            content=None,
            content_json={"nested": {"items": [{"id": "item-empty", "source_citation_ids": ["stale"]}]}},
            item_citation_chunk_ids={"item-empty": ["fabricated-chunk"]},
        )

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(lambda provider: CitationGenerator(build_output)),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert content.content_json["nested"]["items"][0]["source_citation_ids"] == []
    assert list(
        db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars()
    ) == []


def test_generate_content_clears_omitted_stale_ids_without_touching_nested_option_ids(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="omitted-binding", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    def build_output(batches: tuple[MaterialContextBatch, ...]) -> GeneratorOutput:
        return GeneratorOutput(
            title="Omitted bindings",
            content=None,
            content_json={
                "items": [
                    {
                        "id": "item-with-stale-citations",
                        "source_citation_ids": ["untrusted-citation"],
                        "options": [{"id": "option-a", "text": "Choice A"}],
                    }
                ]
            },
            item_citation_chunk_ids={},
        )

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(lambda provider: CitationGenerator(build_output)),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    item = content.content_json["items"][0]
    assert item["source_citation_ids"] == []
    assert "source_citation_ids" not in item["options"][0]
    assert list(db.execute(select(SourceCitation)).scalars()) == []


def test_generate_content_uses_zero_page_index_when_citation_location_is_unknown(
    db: Session,
    tmp_path: Path,
) -> None:
    user = register_user(db, UserCreate(username="null-location", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(placeholder_factory),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    citation = db.execute(
        select(SourceCitation).where(SourceCitation.generated_content_id == content.id)
    ).scalar_one()
    assert content.generation_status == "success"
    assert citation.page is None
    assert citation.page_index == 0
    assert content.content_json["items"][0]["source_citation_ids"] == [citation.id]


def test_generate_content_commits_content_and_citations_once(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, UserCreate(username="single-commit", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    material = create_parsed_material(db, tmp_path, user.id, course.id)
    chunk = _material_chunks(db, material.id)[0]
    chunk.page = "1"
    db.commit()
    commit_calls = 0
    real_commit = db.commit

    def recording_commit() -> None:
        nonlocal commit_calls
        commit_calls += 1
        real_commit()

    monkeypatch.setattr(db, "commit", recording_commit)
    content = generate_content(
        db,
        user_id=user.id,
        course_id=course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_with(placeholder_factory),
        model_provider=MockModelProvider(),
        max_batch_tokens=100,
    )

    assert commit_calls == 1
    assert db.get(AIGeneratedContent, content.id) is not None
    assert len(
        list(db.execute(select(SourceCitation).where(SourceCitation.generated_content_id == content.id)).scalars())
    ) == 1


def test_generate_content_rolls_back_content_when_citation_persistence_fails(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, UserCreate(username="citation-rollback", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(db, tmp_path, user.id, course.id)

    def fail_citation_persistence(session: Session, citations: list[SourceCitation]) -> None:
        raise RuntimeError("citation insert failed")

    monkeypatch.setattr(orchestrator_service, "add_generated_content_citations", fail_citation_persistence)
    with pytest.raises(RuntimeError, match="citation insert failed"):
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(placeholder_factory),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )

    assert list(db.execute(select(AIGeneratedContent)).scalars()) == []
    assert list(db.execute(select(SourceCitation)).scalars()) == []


def test_generate_content_rolls_back_after_real_citation_integrity_error(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, UserCreate(username="integrity-rollback", password="password123"))
    course = create_course(db, user.id, CourseCreate(name="Linear Algebra"))
    create_parsed_material(
        db,
        tmp_path,
        user.id,
        course.id,
        content="First chunk\n\nSecond chunk",
    )

    def build_output(batches: tuple[MaterialContextBatch, ...]) -> GeneratorOutput:
        delivered = [chunk for batch in batches for chunk in batch.chunks]
        return GeneratorOutput(
            title="Duplicate citation IDs",
            content=None,
            content_json={"items": [{"id": "item-a", "source_citation_ids": []}]},
            item_citation_chunk_ids={"item-a": [chunk.chunk_id for chunk in delivered]},
        )

    monkeypatch.setattr(orchestrator_service, "_new_citation_id", lambda: "cit_duplicate")
    with pytest.raises(IntegrityError):
        generate_content(
            db,
            user_id=user.id,
            course_id=course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_with(lambda provider: CitationGenerator(build_output)),
            model_provider=MockModelProvider(),
            max_batch_tokens=100,
        )

    assert list(db.execute(select(AIGeneratedContent)).scalars()) == []
    assert list(db.execute(select(SourceCitation)).scalars()) == []
