from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.integrations.model_provider.openai import OpenAIModelProvider
from app.modules.material_context.schemas import ContextChunk


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("Response", (), {"output_text": "OpenAI answer"})()


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_openai_model_provider_requires_api_key() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        OpenAIModelProvider(
            api_key=None,
            model="gpt-test",
            api_key_env_name="COURSE_QA_API_KEY",
        )

    assert exc_info.value.code == "GENERATION_FAILED"
    assert exc_info.value.details == {"missing": "COURSE_QA_API_KEY"}


def test_openai_model_provider_uses_sdk_client() -> None:
    fake_client = FakeClient()
    chunk = ContextChunk(
        material_id="mat_1",
        chunk_id="chk_1",
        material_name="notes.md",
        page=None,
        page_index=0,
        heading="Intro",
        content_text="Alpha",
    )

    provider = OpenAIModelProvider(api_key="test-key", model="gpt-test", client=fake_client)
    answer = provider.answer_question(question="What is Alpha?", context_chunks=[chunk])

    assert answer.answer_text == "OpenAI answer"
    assert answer.citation_chunk_ids == ["chk_1"]
    assert fake_client.responses.calls[0]["model"] == "gpt-test"
