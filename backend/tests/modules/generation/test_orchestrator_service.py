from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.course_qa.models import SourceCitation
from app.modules.generated_content.models import AIGeneratedContent
from app.modules.generation.orchestrator.contracts import GenerateContentRequest, GeneratorOutput
from app.modules.generation.orchestrator.service import generate_content
from app.modules.material_context.schemas import MaterialGenerationContext, MaterialScope


class RecordingGenerator:
    content_type = "outline"

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider
        self.contexts: list[MaterialGenerationContext] = []

    def generate(
        self,
        *,
        context: MaterialGenerationContext,
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        self.contexts.append(context)
        return GeneratorOutput(
            title="Outline",
            content_json={"sections": [{"id": "sec_001", "title": "Result", "sort_order": 1}]},
        )


class ErrorGenerator(RecordingGenerator):
    def __init__(self, provider: ModelProvider, code: str) -> None:
        super().__init__(provider)
        self.code = code

    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput:
        raise CourseNexusError(code=self.code, message="generation failed", status_code=502)


def test_generate_content_delivers_all_materials_once_without_citations(
    db: Session,
    alice_user,
    owned_course,
    parsed_materials,
    registry_factory,
) -> None:
    generator: RecordingGenerator | None = None

    def factory(provider: ModelProvider) -> RecordingGenerator:
        nonlocal generator
        generator = RecordingGenerator(provider)
        return generator

    content = generate_content(
        db,
        user_id=alice_user.id,
        course_id=owned_course.id,
        payload=GenerateContentRequest(content_type="outline", material_scope=MaterialScope()),
        registry=registry_factory("outline", factory),
        model_provider=MockModelProvider(),
        max_context_tokens=10_000,
    )

    assert generator is not None
    assert len(generator.contexts) == 1
    assert set(generator.contexts[0].material_ids) == {material.id for material in parsed_materials}
    assert all(material.name in generator.contexts[0].text for material in parsed_materials)
    assert content.generation_status == "success"
    assert content.material_scope_json == {
        "include_all_parsed_materials": True,
        "material_ids": [],
        "source_materials": [
            {"material_id": material.id, "material_name": material.name}
            for material in sorted(parsed_materials, key=lambda item: item.id)
        ],
        "material_versions": [
            {"material_id": material.id, "version_id": material.active_parse_version_id}
            for material in sorted(parsed_materials, key=lambda item: item.id)
        ],
    }
    assert db.scalar(select(func.count()).select_from(SourceCitation)) == 0


def test_context_too_large_does_not_call_generator_or_create_history(
    db: Session,
    alice_user,
    owned_course,
    parsed_materials,
    registry_factory,
) -> None:
    generator = RecordingGenerator(MockModelProvider())

    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=alice_user.id,
            course_id=owned_course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_factory("outline", lambda provider: generator),
            model_provider=MockModelProvider(),
            max_context_tokens=1,
        )

    assert exc_info.value.code == "MATERIAL_CONTEXT_TOO_LARGE"
    assert generator.contexts == []
    assert db.scalar(select(func.count()).select_from(AIGeneratedContent)) == 0


def test_no_parsed_material_does_not_create_history(
    db: Session,
    alice_user,
    owned_course,
    registry_factory,
) -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        generate_content(
            db,
            user_id=alice_user.id,
            course_id=owned_course.id,
            payload=GenerateContentRequest(content_type="outline"),
            registry=registry_factory("outline", RecordingGenerator),
            model_provider=MockModelProvider(),
            max_context_tokens=100,
        )
    assert exc_info.value.code == "NO_PARSED_MATERIAL"
    assert db.scalar(select(func.count()).select_from(AIGeneratedContent)) == 0


@pytest.mark.parametrize("code", ["GENERATION_FAILED", "GENERATION_SCHEMA_INVALID"])
def test_generation_failure_creates_failed_history(
    db: Session,
    alice_user,
    owned_course,
    parsed_materials,
    registry_factory,
    code: str,
) -> None:
    content = generate_content(
        db,
        user_id=alice_user.id,
        course_id=owned_course.id,
        payload=GenerateContentRequest(content_type="outline"),
        registry=registry_factory("outline", lambda provider: ErrorGenerator(provider, code)),
        model_provider=MockModelProvider(),
        max_context_tokens=10_000,
    )
    assert content.generation_status == "failed"
    assert content.error_code == code
