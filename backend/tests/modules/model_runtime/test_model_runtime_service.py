from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.errors import CourseNexusError
from app.modules.model_runtime import service
from app.modules.model_runtime.schemas import ModelRuntimeConfigUpdate


class SettingsProvider:
    def __init__(self, env_path: Path) -> None:
        self.env_path = env_path
        self.cache_clear_count = 0

    def __call__(self) -> Settings:
        return Settings(_env_file=self.env_path)

    def cache_clear(self) -> None:
        self.cache_clear_count += 1


class RagManagerProbe:
    def __init__(self) -> None:
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1


def config_payload(
    *,
    embedding_key: str | None = "embedding-secret-key",
    general_key: str | None = "general-secret-key",
) -> ModelRuntimeConfigUpdate:
    return ModelRuntimeConfigUpdate.model_validate(
        {
            "embedding": {
                "model": "text-embedding-v2",
                "base_url": "https://embedding.example/v1/",
                "api_key": embedding_key,
            },
            "general": {
                "model": "general-chat-v3",
                "base_url": "https://models.example/v1/",
                "api_key": general_key,
            },
        }
    )


def test_build_config_only_returns_key_prefixes() -> None:
    settings = Settings(
        _env_file=None,
        embedding_api_key="embedding-complete-secret",
        embedding_base_url="https://embedding.example/v1",
        embedding_model="embedding-model",
        **{
            f"{purpose}_{field}": value
            for purpose in service.GENERAL_MODEL_PURPOSES
            for field, value in (
                ("api_key", "general-complete-secret"),
                ("base_url", "https://models.example/v1"),
                ("model", "general-model"),
            )
        },
    )

    result = service.build_model_runtime_config(settings)
    serialized = result.model_dump_json()

    assert result.embedding.api_key_hint == "embe••••"
    assert result.general.api_key_hint == "gene••••"
    assert result.general_config_consistent is True
    assert "embedding-complete-secret" not in serialized
    assert "general-complete-secret" not in serialized


def test_build_config_reports_divergent_general_endpoints() -> None:
    settings = Settings(
        _env_file=None,
        course_qa_api_key="course-key",
        course_qa_base_url="https://course.example/v1",
        course_qa_model="course-model",
        quiz_api_key="quiz-key",
        quiz_base_url="https://quiz.example/v1",
        quiz_model="quiz-model",
    )

    result = service.build_model_runtime_config(settings)

    assert result.general.model == "course-model"
    assert result.general_config_consistent is False


def test_save_updates_all_general_purposes_and_preserves_unrelated_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# Keep this comment\n"
        "DATABASE_URL=sqlite:///./custom.db\n"
        "CUSTOM_SETTING=keep-me\n"
        "EMBEDDING_API_KEY=old-embedding-key\n"
        "COURSE_QA_API_KEY=old-general-key\n",
        encoding="utf-8",
    )
    settings_provider = SettingsProvider(env_path)
    rag_manager = RagManagerProbe()
    refreshed_settings: list[Settings] = []
    monkeypatch.setattr(service, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(service, "get_settings", settings_provider)
    monkeypatch.setattr(service, "get_rag_index_manager", lambda: rag_manager)
    monkeypatch.setattr(
        service,
        "refresh_logging_redactor",
        lambda settings: refreshed_settings.append(settings),
    )

    result = service.save_model_runtime_config(config_payload())
    saved = env_path.read_text(encoding="utf-8")
    reloaded = Settings(_env_file=env_path)

    assert "# Keep this comment" in saved
    assert "CUSTOM_SETTING=keep-me" in saved
    assert reloaded.embedding_api_key == "embedding-secret-key"
    assert reloaded.embedding_base_url == "https://embedding.example/v1"
    assert reloaded.embedding_model == "text-embedding-v2"
    for purpose in service.GENERAL_MODEL_PURPOSES:
        assert getattr(reloaded, f"{purpose}_api_key") == "general-secret-key"
        assert getattr(reloaded, f"{purpose}_base_url") == "https://models.example/v1"
        assert getattr(reloaded, f"{purpose}_model") == "general-chat-v3"
    assert result.general_config_consistent is True
    assert result.embedding.api_key_hint == "embe••••"
    assert result.general.api_key_hint == "gene••••"
    assert "embedding-secret-key" not in result.model_dump_json()
    assert "general-secret-key" not in result.model_dump_json()
    assert rag_manager.close_count == 1
    assert settings_provider.cache_clear_count == 1
    assert len(refreshed_settings) == 1
    assert list((tmp_path / "tmp").iterdir()) == []


def test_save_keeps_existing_keys_when_key_fields_are_blank(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "EMBEDDING_API_KEY=old-embedding-key\n"
        "COURSE_QA_API_KEY=old-general-key\n"
        "QUIZ_API_KEY=different-key\n",
        encoding="utf-8",
    )
    settings_provider = SettingsProvider(env_path)
    monkeypatch.setattr(service, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(service, "get_settings", settings_provider)
    monkeypatch.setattr(service, "get_rag_index_manager", RagManagerProbe)
    monkeypatch.setattr(service, "refresh_logging_redactor", lambda _settings: None)

    service.save_model_runtime_config(
        config_payload(embedding_key=None, general_key=None)
    )
    reloaded = Settings(_env_file=env_path)

    assert reloaded.embedding_api_key == "old-embedding-key"
    for purpose in service.GENERAL_MODEL_PURPOSES:
        assert getattr(reloaded, f"{purpose}_api_key") == "old-general-key"


def test_first_save_requires_both_api_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    settings_provider = SettingsProvider(env_path)
    monkeypatch.setattr(service, "ENV_FILE_PATH", env_path)
    monkeypatch.setattr(service, "get_settings", settings_provider)

    with pytest.raises(CourseNexusError) as exc_info:
        service.save_model_runtime_config(
            config_payload(embedding_key=None, general_key=None)
        )

    assert exc_info.value.code == "MODEL_API_KEY_REQUIRED"
    assert exc_info.value.details == {"groups": ["embedding", "general"]}
    assert not env_path.exists()


@pytest.mark.parametrize(
    "base_url",
    ["not-a-url", "ftp://models.example/v1", "https://user:pass@models.example/v1"],
)
def test_config_rejects_unsafe_base_urls(base_url: str) -> None:
    payload = config_payload().model_dump(mode="json")
    payload["general"]["base_url"] = base_url

    with pytest.raises(ValueError):
        ModelRuntimeConfigUpdate.model_validate(payload)
