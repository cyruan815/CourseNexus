from __future__ import annotations

import pytest

import app.modules.course_qa.router as course_qa_router
from app.core.config import Settings
from app.integrations.model_provider.mock import MockModelProvider


def test_course_qa_provider_uses_its_own_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(
        course_qa_router,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            course_qa_api_key="qa-key",
            course_qa_base_url="https://qa.example/v1",
            course_qa_model="qa-model",
            embedding_api_key="embedding-key",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="embedding-model",
        ),
    )
    monkeypatch.setattr(course_qa_router, "OpenAIModelProvider", FakeProvider)

    provider = course_qa_router.get_model_provider()

    assert provider is not None
    assert captured == {
        "api_key": "qa-key",
        "model": "qa-model",
        "base_url": "https://qa.example/v1",
        "api_key_env_name": "COURSE_QA_API_KEY",
    }


def test_course_qa_provider_does_not_reuse_embedding_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        course_qa_router,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
            course_qa_api_key=None,
        ),
    )

    assert isinstance(course_qa_router.get_model_provider(), MockModelProvider)
