from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.core.errors import CourseNexusError
from app.integrations.model_provider.openai import OpenAIModelProvider


class ReferenceExtraction(BaseModel):
    facts: list[str]
    citation_chunk_ids: list[str]


class FakeResponses:
    def __init__(self, *, parsed=None, error: Exception | None = None) -> None:
        self.parsed = parsed
        self.error = error
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return type("ParsedResponse", (), {"output_parsed": self.parsed})()


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def test_openai_provider_returns_project_schema() -> None:
    parsed = ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    responses = FakeResponses(parsed=parsed)
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(responses),
    )

    result = provider.generate_structured(
        prompt="reference extraction",
        output_schema=ReferenceExtraction,
    )

    assert result == parsed
    assert responses.calls == [
        {
            "model": "test-model",
            "input": "reference extraction",
            "text_format": ReferenceExtraction,
        }
    ]


def test_openai_provider_maps_sdk_error_to_generation_failed() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(error=RuntimeError("network"))),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    assert exc_info.value.code == "GENERATION_FAILED"


def test_openai_provider_maps_sdk_parse_validation_error_to_schema_invalid() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(error=_schema_validation_error())),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_openai_provider_maps_invalid_parsed_data_to_schema_invalid() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(parsed={"facts": ["A"]})),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def _schema_validation_error() -> Exception:
    try:
        ReferenceExtraction.model_validate({"facts": ["A"]})
    except Exception as exc:
        return exc
    raise AssertionError("Expected schema validation to fail")
