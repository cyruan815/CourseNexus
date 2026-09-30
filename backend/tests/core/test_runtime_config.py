import pytest
from pydantic import ValidationError

from app.core.config import MODEL_PURPOSES, ROOT_DIR, Settings


def _production_model_keys() -> dict[str, str]:
    return {f"{purpose}_api_key": f"{purpose}-key" for purpose in MODEL_PURPOSES}


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_app_environment_accepts_supported_values(app_env: str) -> None:
    settings = Settings(_env_file=None, app_env=app_env)

    assert settings.app_env == app_env


def test_production_environment_accepts_strong_secret() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        secret_key="a-production-secret-that-is-long-enough",
        **_production_model_keys(),
    )

    assert settings.app_env == "production"


def test_app_environment_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")


@pytest.mark.parametrize(
    "secret_key",
    ["", "   ", "replace-with-local-dev-secret", "too-short"],
)
def test_production_environment_rejects_unsafe_secret(secret_key: str) -> None:
    with pytest.raises(ValidationError, match="production SECRET_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key=secret_key,
            **_production_model_keys(),
        )


def test_non_production_environment_keeps_development_secret_compatibility() -> None:
    assert Settings(_env_file=None, app_env="development").secret_key == "replace-with-local-dev-secret"
    assert Settings(_env_file=None, app_env="test").secret_key == "replace-with-local-dev-secret"


def test_production_environment_rejects_missing_model_api_key() -> None:
    configured_keys = _production_model_keys()
    configured_keys["handout_api_key"] = "   "

    with pytest.raises(ValidationError, match="handout"):
        Settings(
            _env_file=None,
            app_env="production",
            secret_key="a-production-secret-that-is-long-enough",
            **configured_keys,
        )


def test_development_environment_allows_unconfigured_model_endpoints() -> None:
    settings = Settings(_env_file=None, app_env="development")

    assert all(settings.model_endpoint(purpose).api_key is None for purpose in MODEL_PURPOSES)


def test_mock_model_provider_is_disabled_by_default() -> None:
    assert Settings(_env_file=None).enable_mock_model_provider is False


def test_default_sqlite_url_resolves_from_project_root() -> None:
    assert Settings(_env_file=None).database_url == (
        f"sqlite:///{(ROOT_DIR / 'course_nexus.db').as_posix()}"
    )


def test_memory_sqlite_url_remains_in_memory() -> None:
    assert (
        Settings(_env_file=None, database_url="sqlite:///:memory:").database_url
        == "sqlite:///:memory:"
    )


def test_default_upload_path_resolves_from_project_root() -> None:
    assert Settings(_env_file=None).file_storage_path == str(ROOT_DIR / "uploads")


def test_default_log_path_resolves_from_project_root() -> None:
    assert Settings(_env_file=None).log_dir == str(ROOT_DIR / "logs")


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_non_production_environment_allows_explicit_mock_mode(app_env: str) -> None:
    settings = Settings(
        _env_file=None,
        app_env=app_env,
        enable_mock_model_provider=True,
    )

    assert settings.enable_mock_model_provider is True


def test_production_environment_rejects_mock_mode() -> None:
    with pytest.raises(ValidationError, match="mock model provider"):
        Settings(
            _env_file=None,
            app_env="production",
            enable_mock_model_provider=True,
            secret_key="a-production-secret-that-is-long-enough",
            **_production_model_keys(),
        )
