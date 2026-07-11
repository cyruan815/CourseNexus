from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, signature
from types import SimpleNamespace
from typing import Any, get_args, get_origin, get_type_hints

import pytest
from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.placeholder_generators import PlaceholderGenerator
from app.modules.generation.orchestrator import registry as registry_module
from app.modules.generation.orchestrator.contracts import (
    GenerateContentRequest,
    Generator,
    GeneratorFactory,
    GeneratorOutput,
)
from app.modules.generation.orchestrator.registry import GeneratorRegistry, default_generator_registry
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch, MaterialScope


def _factory(content_type: str, marker: str = "default"):
    return lambda provider: SimpleNamespace(
        content_type=content_type,
        marker=marker,
        model_provider=provider,
    )


def _batch(*, chunk_id: str = "chunk-1", content_text: str = "First delivered chunk") -> MaterialContextBatch:
    return MaterialContextBatch(
        chunks=[
            ContextChunk(
                material_id="material-1",
                chunk_id=chunk_id,
                material_name="notes.md",
                page=None,
                page_index=None,
                heading=None,
                content_text=content_text,
            )
        ],
        material_ids=["material-1"],
        estimated_tokens=12,
    )


class _ConcreteGenerator:
    content_type = "outline"

    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        first_chunk = batches[0].chunks[0]
        return GeneratorOutput(
            title="Concrete generator",
            content=first_chunk.content_text,
            content_json={"items": []},
        )


def _build_concrete_generator(model_provider: ModelProvider) -> Generator:
    return _ConcreteGenerator(model_provider)


_CONCRETE_FACTORY: GeneratorFactory = _build_concrete_generator


def test_generate_content_request_defaults_material_scope_and_parameters() -> None:
    request = GenerateContentRequest(content_type="outline")

    assert request.material_scope == MaterialScope()
    assert request.parameters == {}


def test_generate_content_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GenerateContentRequest(content_type="outline", unexpected=True)


@pytest.mark.parametrize("content_type", ["", "x" * 33])
def test_generate_content_request_rejects_content_type_outside_length_bounds(content_type: str) -> None:
    with pytest.raises(ValidationError):
        GenerateContentRequest(content_type=content_type)


@pytest.mark.parametrize("content_type", ["x", "x" * 32])
def test_generate_content_request_accepts_content_type_length_boundaries(content_type: str) -> None:
    assert GenerateContentRequest(content_type=content_type).content_type == content_type


def test_generator_output_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GeneratorOutput(title="Outline", content_json={}, unexpected=True)


@pytest.mark.parametrize("title", ["", "x" * 256])
def test_generator_output_rejects_title_outside_length_bounds(title: str) -> None:
    with pytest.raises(ValidationError):
        GeneratorOutput(title=title, content_json={})


@pytest.mark.parametrize("title", ["x", "x" * 255])
def test_generator_output_accepts_title_length_boundaries(title: str) -> None:
    assert GeneratorOutput(title=title, content_json={}).title == title


def test_generator_output_accepts_nullable_content() -> None:
    assert GeneratorOutput(title="Outline", content_json={}).content is None
    assert GeneratorOutput(title="Outline", content="Body", content_json={}).content == "Body"


@pytest.mark.parametrize("content_json", [None, []])
def test_generator_output_rejects_non_dictionary_content_json(content_json: object) -> None:
    with pytest.raises(ValidationError):
        GeneratorOutput(title="Outline", content_json=content_json)


def test_generator_output_requires_content_json() -> None:
    with pytest.raises(ValidationError):
        GeneratorOutput(title="Outline")


def test_generator_output_supports_default_and_explicit_item_citation_bindings() -> None:
    default_output = GeneratorOutput(title="Outline", content_json={})
    explicit_output = GeneratorOutput(
        title="Outline",
        content_json={},
        item_citation_chunk_ids={"item_001": ["chunk-1", "chunk-2"]},
    )

    assert default_output.item_citation_chunk_ids == {}
    assert explicit_output.item_citation_chunk_ids == {"item_001": ["chunk-1", "chunk-2"]}


def test_generator_protocol_freezes_keyword_only_generate_signature() -> None:
    generate_signature = signature(Generator.generate)
    assert tuple(generate_signature.parameters) == (
        "self",
        "batches",
        "expected_material_ids",
        "parameters",
    )
    assert generate_signature.parameters["self"].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert generate_signature.parameters["batches"].kind is Parameter.KEYWORD_ONLY
    assert generate_signature.parameters["expected_material_ids"].kind is Parameter.KEYWORD_ONLY
    assert generate_signature.parameters["parameters"].kind is Parameter.KEYWORD_ONLY

    type_hints = get_type_hints(Generator.generate)
    assert type_hints == {
        "batches": tuple[MaterialContextBatch, ...],
        "expected_material_ids": frozenset[str],
        "parameters": dict[str, Any],
        "return": GeneratorOutput,
    }


def test_generator_factory_freezes_provider_to_generator_callable_shape() -> None:
    assert get_origin(GeneratorFactory) is Callable
    assert get_args(GeneratorFactory) == ([ModelProvider], Generator)

    provider = MockModelProvider()
    generator = _CONCRETE_FACTORY(provider)
    output = generator.generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"material-1"}),
        parameters={},
    )

    assert generator.content_type == "outline"
    assert isinstance(generator, _ConcreteGenerator)
    assert generator.model_provider is provider
    assert output.content == "First delivered chunk"


def test_generator_registry_factory_receives_exact_model_provider() -> None:
    registry = GeneratorRegistry()
    provider = object()
    registry.register("outline", _factory("outline"))

    generator = registry.create("outline", provider)

    assert generator.content_type == "outline"
    assert generator.model_provider is provider


def test_generator_registry_rejects_unknown_content_type() -> None:
    registry = GeneratorRegistry()

    with pytest.raises(CourseNexusError) as exc_info:
        registry.create("unknown", object())

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.status_code == 422


def test_generator_registry_rejects_duplicate_registration_without_replace() -> None:
    registry = GeneratorRegistry()
    registry.register("outline", _factory("outline", "first"))

    with pytest.raises(CourseNexusError) as exc_info:
        registry.register("outline", _factory("outline", "second"))

    assert exc_info.value.code == "CONFLICT"
    assert exc_info.value.status_code == 409


def test_generator_registry_replace_updates_factory() -> None:
    registry = GeneratorRegistry()
    registry.register("outline", _factory("outline", "first"))

    registry.register("outline", _factory("outline", "second"), replace=True)

    assert registry.create("outline", object()).marker == "second"


def test_generator_registry_supported_content_types_are_stably_sorted() -> None:
    registry = GeneratorRegistry()
    registry.register("quiz", _factory("quiz"))
    registry.register("flashcard", _factory("flashcard"))
    registry.register("outline", _factory("outline"))

    assert registry.supported_content_types() == ("flashcard", "outline", "quiz")


def test_default_generator_registry_supports_exactly_five_builtin_types() -> None:
    registry = default_generator_registry()

    assert registry.supported_content_types() == (
        "flashcard",
        "knowledge_list",
        "mindmap",
        "outline",
        "quiz",
    )


def test_default_registry_discovers_concrete_module_build_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "app.modules.generation.generators.quiz.generator"
    imported_modules: list[str] = []

    def build_generator(provider: object) -> SimpleNamespace:
        return SimpleNamespace(content_type="quiz", model_provider=provider, source="concrete")

    def import_module(name: str) -> SimpleNamespace:
        imported_modules.append(name)
        return SimpleNamespace(build_generator=build_generator)

    monkeypatch.setattr(registry_module, "BUILTIN_GENERATOR_MODULES", {"quiz": module_name})
    monkeypatch.setattr(registry_module, "import_module", import_module)

    registry = default_generator_registry()
    generator = registry.create("quiz", object())

    assert imported_modules == [module_name]
    assert generator.source == "concrete"


def test_default_registry_uses_placeholder_only_when_target_module_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "app.modules.generation.generators.quiz.generator"

    def import_module(name: str) -> None:
        raise ModuleNotFoundError(f"No module named {name!r}", name=name)

    monkeypatch.setattr(registry_module, "BUILTIN_GENERATOR_MODULES", {"quiz": module_name})
    monkeypatch.setattr(registry_module, "import_module", import_module)

    registry = default_generator_registry()
    provider = object()
    generator = registry.create("quiz", provider)

    assert isinstance(generator, PlaceholderGenerator)
    assert generator.model_provider is provider


def test_default_registry_does_not_swallow_missing_internal_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = "app.modules.generation.generators.quiz.generator"

    def import_module(name: str) -> None:
        raise ModuleNotFoundError("No module named 'broken_dependency'", name="broken_dependency")

    monkeypatch.setattr(registry_module, "BUILTIN_GENERATOR_MODULES", {"quiz": module_name})
    monkeypatch.setattr(registry_module, "import_module", import_module)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        default_generator_registry()

    assert exc_info.value.name == "broken_dependency"


@pytest.mark.parametrize(
    ("content_type", "collection_key", "item_id"),
    [
        ("flashcard", "cards", "flashcard-1"),
        ("knowledge_list", "knowledge_points", "knowledge-point-1"),
        ("mindmap", "nodes", "mindmap-root"),
        ("outline", "items", "outline-item-1"),
        ("quiz", "questions", "quiz-question-1"),
    ],
)
def test_placeholder_generator_returns_stable_type_specific_item(
    content_type: str,
    collection_key: str,
    item_id: str,
) -> None:
    generator = PlaceholderGenerator(content_type=content_type, model_provider=object())
    batches = (
        _batch(),
        _batch(chunk_id="chunk-2", content_text="Later delivered chunk"),
    )

    first_output = generator.generate(
        batches=batches,
        expected_material_ids=frozenset({"material-1"}),
        parameters={},
    )
    second_output = generator.generate(
        batches=batches,
        expected_material_ids=frozenset({"material-1"}),
        parameters={},
    )

    assert first_output == second_output
    assert first_output.content == "First delivered chunk"
    assert first_output.content_json[collection_key][0]["id"] == item_id
    assert first_output.content_json[collection_key][0]["source_citation_ids"] == []
    assert first_output.item_citation_chunk_ids == {item_id: ["chunk-1"]}
