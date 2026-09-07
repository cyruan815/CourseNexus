from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel

from app.core.errors import CourseNexusError
from app.integrations.model_provider.openai import OpenAIModelProvider


class ReferenceExtraction(BaseModel):
    facts: list[str]
    citation_chunk_ids: list[str]


class FakeResponses:
    def __init__(self, *, parsed=None, error: Exception | None = None, usage=None) -> None:
        self.parsed = parsed
        self.error = error
        self.usage = usage
        self.calls: list[dict[str, object]] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return type("ParsedResponse", (), {"output_parsed": self.parsed, "usage": self.usage})()


class FakeChatCompletions:
    def __init__(self, *, content: str, usage=None) -> None:
        self.content = content
        self.usage = usage
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("ChatCompletion", (), {"choices": [choice], "usage": self.usage})()


class FakeChat:
    def __init__(self, completions: FakeChatCompletions) -> None:
        self.completions = completions


class FakeClient:
    def __init__(self, responses: FakeResponses, *, chat: FakeChat | None = None) -> None:
        self.responses = responses
        self.chat = chat


class FakeResponsesApiNotFoundError(Exception):
    status_code = 404


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


def test_openai_provider_falls_back_to_chat_completions_when_responses_api_is_not_found() -> None:
    responses = FakeResponses(error=FakeResponsesApiNotFoundError("not found"))
    chat_completions = FakeChatCompletions(content='{"facts":["A"],"citation_chunk_ids":["c1"]}')
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    result = provider.generate_structured(
        prompt="reference extraction",
        output_schema=ReferenceExtraction,
    )

    assert result == ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    assert chat_completions.calls[0]["model"] == "test-model"
    assert chat_completions.calls[0]["response_format"] == {"type": "json_object"}


def test_deepseek_provider_uses_chat_completions_without_calling_responses_api() -> None:
    responses = FakeResponses(error=AssertionError("Responses API must not be used"))
    chat_completions = FakeChatCompletions(content='{"facts":["A"],"citation_chunk_ids":["c1"]}')
    provider = OpenAIModelProvider(
        api_key="test",
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    result = provider.generate_structured(
        prompt="reference extraction",
        output_schema=ReferenceExtraction,
    )

    assert result == ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    assert responses.calls == []
    assert chat_completions.calls[0]["model"] == "deepseek-v4-flash"
    assert "reference extraction" in chat_completions.calls[0]["messages"][1]["content"]


def test_auto_style_uses_responses_for_openai_compatible_url() -> None:
    parsed = ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    responses = FakeResponses(parsed=parsed)
    chat_completions = FakeChatCompletions(content='{"facts":[],"citation_chunk_ids":[]}')
    provider = OpenAIModelProvider(
        api_key="test",
        model="gpt-test",
        base_url="https://api.openai.com/v1",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    assert provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction) == parsed
    assert len(responses.calls) == 1
    assert chat_completions.calls == []


def test_explicit_api_style_overrides_url_detection() -> None:
    parsed = ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    chat_completions = FakeChatCompletions(content='{"facts":["A"],"citation_chunk_ids":["c1"]}')
    responses_provider = OpenAIModelProvider(
        api_key="test",
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_style="responses",
        client=FakeClient(FakeResponses(parsed=parsed), chat=FakeChat(chat_completions)),
    )
    assert responses_provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction) == parsed
    assert len(responses_provider.client.responses.calls) == 1
    assert chat_completions.calls == []

    responses = FakeResponses(error=AssertionError("Responses API must not be used"))
    chat_completions = FakeChatCompletions(content='{"facts":["A"],"citation_chunk_ids":["c1"]}')
    response_provider = OpenAIModelProvider(
        api_key="test",
        model="gpt-test",
        base_url="https://api.openai.com/v1",
        api_style="chat",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )
    assert response_provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction) == parsed
    assert responses.calls == []
    assert len(chat_completions.calls) == 1


def test_structured_generation_logs_chat_usage(caplog) -> None:
    responses = FakeResponses(error=FakeResponsesApiNotFoundError("not found"))
    chat_completions = FakeChatCompletions(
        content='{"facts":["A"],"citation_chunk_ids":["c1"]}',
        usage={"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168},
    )
    provider = OpenAIModelProvider(
        api_key="test",
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    with caplog.at_level(logging.INFO, logger="course_nexus.model.generate"):
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    record = next(record for record in caplog.records if record.name.endswith("model.generate"))
    message = record.getMessage()
    assert "prompt_tokens=123" in message
    assert "completion_tokens=45" in message
    assert "total_tokens=168" in message
    assert "usage_status=available" in message


def test_structured_generation_normalizes_responses_usage(caplog) -> None:
    parsed = ReferenceExtraction(facts=["A"], citation_chunk_ids=["c1"])
    responses = FakeResponses(
        parsed=parsed,
        usage={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
    )
    provider = OpenAIModelProvider(
        api_key="test",
        model="gpt-test",
        client=FakeClient(responses),
    )

    with caplog.at_level(logging.INFO, logger="course_nexus.model.generate"):
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    record = next(record for record in caplog.records if record.name.endswith("model.generate"))
    message = record.getMessage()
    assert "prompt_tokens=11" in message
    assert "completion_tokens=7" in message
    assert "total_tokens=18" in message
    assert "usage_status=available" in message


def test_openai_provider_maps_sdk_error_to_generation_failed() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(error=RuntimeError("network"))),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    assert exc_info.value.code == "GENERATION_FAILED"
    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_openai_provider_maps_sdk_parse_validation_error_to_schema_invalid() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(error=_schema_validation_error())),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    _assert_schema_invalid_error(exc_info.value)


def test_openai_provider_maps_chat_json_parse_error_to_schema_invalid() -> None:
    responses = FakeResponses(error=FakeResponsesApiNotFoundError("not found"))
    chat_completions = FakeChatCompletions(content="{not-json")
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    _assert_schema_invalid_error(exc_info.value)


def test_openai_provider_maps_invalid_parsed_data_to_schema_invalid() -> None:
    provider = OpenAIModelProvider(
        api_key="test",
        model="test-model",
        client=FakeClient(FakeResponses(parsed={"facts": ["A"]})),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        provider.generate_structured(prompt="reference extraction", output_schema=ReferenceExtraction)

    _assert_schema_invalid_error(exc_info.value)


def _assert_schema_invalid_error(error: CourseNexusError) -> None:
    assert error.code == "GENERATION_SCHEMA_INVALID"
    assert error.status_code == 500


def _schema_validation_error() -> Exception:
    try:
        ReferenceExtraction.model_validate({"facts": ["A"]})
    except Exception as exc:
        return exc
    raise AssertionError("Expected schema validation to fail")
