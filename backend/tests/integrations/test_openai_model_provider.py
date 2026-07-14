from __future__ import annotations

import logging
import pytest

from app.core.errors import CourseNexusError
from app.integrations.model_provider.openai import OpenAIModelProvider
from app.modules.material_context.schemas import ContextChunk


class FakeResponses:
    def __init__(self, *, error: Exception | None = None, output_text: str = "OpenAI answer [[cite:1]]") -> None:
        self.error = error
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return type("Response", (), {"output_text": self.output_text})()


class FakeChatCompletions:
    def __init__(self, *, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        message = type("Message", (), {"content": self.content})()
        choice = type("Choice", (), {"message": message})()
        return type("ChatCompletion", (), {"choices": [choice]})()


class FakeChat:
    def __init__(self, completions: FakeChatCompletions) -> None:
        self.completions = completions


class FakeClient:
    def __init__(self, responses: FakeResponses | None = None, *, chat: FakeChat | None = None) -> None:
        self.responses = responses or FakeResponses()
        self.chat = chat


class FakeResponsesApiNotFoundError(Exception):
    status_code = 404


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


def test_openai_model_provider_requires_api_key() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        OpenAIModelProvider(
            api_key=None,
            model="gpt-test",
            api_key_env_name="COURSE_QA_API_KEY",
        )

    assert exc_info.value.code == "GENERATION_FAILED"
    assert exc_info.value.details == {"missing": "COURSE_QA_API_KEY"}


def test_openai_model_provider_uses_sdk_client(caplog) -> None:
    logger = capture_course_logs(caplog)
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
    try:
        answer = provider.answer_question(question="What is Alpha?", context_chunks=[chunk])
    finally:
        logger.removeHandler(caplog.handler)

    assert answer.answer_text == "OpenAI answer [[cite:chk_1]]"
    assert answer.citation_chunk_ids == ["chk_1"]
    assert fake_client.responses.calls[0]["model"] == "gpt-test"
    record = next(record for record in caplog.records if record.name.endswith("model.generate"))
    assert "模型调用成功" in record.getMessage()
    assert "operation=answer_question" in record.getMessage()
    assert "model=gpt-test" in record.getMessage()
    assert "chunks=1" in record.getMessage()
    assert "What is Alpha?" not in record.getMessage()
    assert "OpenAI answer" not in record.getMessage()


def test_openai_model_provider_falls_back_to_chat_completions_for_answer_question() -> None:
    responses = FakeResponses(error=FakeResponsesApiNotFoundError("not found"))
    chat_completions = FakeChatCompletions(content="Chat answer [[cite:1]]")
    chunk = ContextChunk(
        material_id="mat_1",
        chunk_id="chk_1",
        material_name="notes.md",
        page=None,
        page_index=0,
        heading="Intro",
        content_text="Alpha",
    )
    provider = OpenAIModelProvider(
        api_key="test-key",
        model="gpt-test",
        client=FakeClient(responses, chat=FakeChat(chat_completions)),
    )

    answer = provider.answer_question(question="What is Alpha?", context_chunks=[chunk])

    assert answer.answer_text == "Chat answer [[cite:chk_1]]"
    assert answer.citation_chunk_ids == ["chk_1"]
    assert responses.calls[0]["model"] == "gpt-test"
    assert chat_completions.calls[0]["model"] == "gpt-test"
    assert chat_completions.calls[0]["messages"][0]["role"] == "system"


def test_openai_model_provider_rejects_out_of_range_citation_markers() -> None:
    fake_client = FakeClient(FakeResponses(output_text="Unsupported [[cite:9]]"))
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

    assert answer.answer_text == "Unsupported "
    assert answer.citation_chunk_ids == []


def test_openai_model_provider_deduplicates_repeated_citations() -> None:
    fake_client = FakeClient(FakeResponses(output_text="Alpha [[cite:1]] again [[cite:1]]"))
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

    assert answer.answer_text == "Alpha [[cite:chk_1]] again [[cite:chk_1]]"
    assert answer.citation_chunk_ids == ["chk_1"]
