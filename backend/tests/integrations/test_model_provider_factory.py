from __future__ import annotations

import pytest

import app.integrations.model_provider.factory as provider_factory
from app.core.config import ModelEndpointConfig, Settings
from app.core.errors import CourseNexusError
from app.integrations.model_provider.mock import MockModelProvider


def test_factory_uses_purpose_specific_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(provider_factory, "OpenAIModelProvider", FakeProvider)
    settings = Settings(
        _env_file=None,
        course_qa_api_key="qa-key",
        course_qa_base_url="https://qa.example/v1",
        course_qa_model="qa-model",
        embedding_api_key="embedding-key",
    )

    provider = provider_factory.create_model_provider("course_qa", settings=settings)

    assert isinstance(provider, FakeProvider)
    assert captured == {
        "api_key": "qa-key",
        "model": "qa-model",
        "base_url": "https://qa.example/v1",
        "api_key_env_name": "COURSE_QA_API_KEY",
        "api_style": "auto",
    }


def test_factory_returns_mock_only_when_explicitly_enabled() -> None:
    settings = Settings(_env_file=None, enable_mock_model_provider=True)

    provider = provider_factory.create_model_provider("course_qa", settings=settings)

    assert isinstance(provider, MockModelProvider)


def test_factory_returns_stable_service_unavailable_error_when_unconfigured() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        provider_factory.create_model_provider(
            "course_qa",
            settings=Settings(_env_file=None),
        )

    assert exc_info.value.code == "MODEL_PROVIDER_NOT_CONFIGURED"
    assert exc_info.value.message == "模型服务未配置"
    assert exc_info.value.status_code == 503
    assert exc_info.value.details == {"purpose": "course_qa"}


def test_factory_treats_whitespace_api_key_as_unconfigured() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        provider_factory.create_model_provider(
            "course_qa",
            settings=Settings(_env_file=None, course_qa_api_key="   "),
        )

    assert exc_info.value.code == "MODEL_PROVIDER_NOT_CONFIGURED"


def test_factory_forwards_requested_api_style(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(provider_factory, "OpenAIModelProvider", FakeProvider)

    provider_factory.create_model_provider(
        "study_plan_generator",
        api_style="responses",
        settings=Settings(_env_file=None, study_plan_generator_api_key="plan-key"),
    )

    assert captured["api_style"] == "responses"


def test_factory_supports_explicit_derived_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(provider_factory, "OpenAIModelProvider", FakeProvider)

    provider_factory.create_model_provider_from_endpoint(
        "study_plan_map",
        endpoint=ModelEndpointConfig(
            api_key="generator-key",
            base_url="https://generator.example/v1",
            model="map-model",
        ),
        api_style="chat",
        settings=Settings(_env_file=None),
    )

    assert captured == {
        "api_key": "generator-key",
        "model": "map-model",
        "base_url": "https://generator.example/v1",
        "api_key_env_name": "STUDY_PLAN_MAP_API_KEY",
        "api_style": "chat",
    }
