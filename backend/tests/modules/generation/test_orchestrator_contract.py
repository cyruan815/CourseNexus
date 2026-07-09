from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.modules.generation.orchestrator.contracts import GenerateContentRequest
from app.modules.generation.orchestrator.registry import GeneratorRegistry
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator


def test_generator_registry_rejects_unknown_content_type() -> None:
    registry = GeneratorRegistry()

    with pytest.raises(CourseNexusError) as exc_info:
        registry.get("unknown")

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_generator_registry_returns_registered_generator() -> None:
    registry = GeneratorRegistry()
    generator = PlaceholderGenerator(content_type="outline")
    registry.register("outline", generator)

    assert registry.get("outline") is generator


def test_generate_content_request_defaults_material_scope() -> None:
    request = GenerateContentRequest(content_type="outline")

    assert request.material_scope.include_all_parsed_materials is True
    assert request.parameters == {}
