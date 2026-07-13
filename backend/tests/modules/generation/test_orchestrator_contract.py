from __future__ import annotations

from collections.abc import Callable
from inspect import Parameter, signature
from typing import Any, get_args, get_origin, get_type_hints

import pytest
from pydantic import ValidationError

from app.integrations.model_provider.base import ModelProvider
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.orchestrator.contracts import (
    GenerateContentRequest,
    Generator,
    GeneratorFactory,
    GeneratorOutput,
)
from app.modules.material_context.schemas import MaterialGenerationContext, MaterialScope


class ConcreteGenerator:
    content_type = "outline"

    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        context: MaterialGenerationContext,
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        return GeneratorOutput(
            title="Concrete generator",
            content=context.text,
            content_json={"items": []},
        )


def build_concrete_generator(model_provider: ModelProvider) -> Generator:
    return ConcreteGenerator(model_provider)


def test_generate_content_request_defaults_material_scope_and_parameters() -> None:
    request = GenerateContentRequest(content_type="outline")
    assert request.material_scope == MaterialScope()
    assert request.parameters == {}


def test_generate_content_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        GenerateContentRequest(content_type="outline", unexpected=True)


def test_generator_output_contains_only_business_result_fields() -> None:
    output = GeneratorOutput(title="Outline", content_json={"sections": []})
    assert output.model_dump() == {
        "title": "Outline",
        "content": None,
        "content_json": {"sections": []},
    }
    with pytest.raises(ValidationError):
        GeneratorOutput(title="Outline", content_json={}, item_citation_chunk_ids={})


def test_generator_protocol_uses_one_complete_context() -> None:
    generate_signature = signature(Generator.generate)
    assert tuple(generate_signature.parameters) == ("self", "context", "parameters")
    assert generate_signature.parameters["context"].kind is Parameter.KEYWORD_ONLY
    assert generate_signature.parameters["parameters"].kind is Parameter.KEYWORD_ONLY
    assert get_type_hints(Generator.generate) == {
        "context": MaterialGenerationContext,
        "parameters": dict[str, Any],
        "return": GeneratorOutput,
    }


def test_generator_factory_keeps_provider_injection() -> None:
    assert get_origin(GeneratorFactory) is Callable
    assert get_args(GeneratorFactory) == ([ModelProvider], Generator)
    provider = MockModelProvider()
    generator = build_concrete_generator(provider)
    context = MaterialGenerationContext(
        chunks=[],
        material_ids=["mat_1"],
        text="Complete context",
        estimated_tokens=4,
    )
    output = generator.generate(context=context, parameters={})
    assert generator.model_provider is provider
    assert output.content == "Complete context"
