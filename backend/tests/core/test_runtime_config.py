import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_app_environment_accepts_supported_values(app_env: str) -> None:
    settings = Settings(_env_file=None, app_env=app_env)

    assert settings.app_env == app_env


def test_production_environment_accepts_strong_secret() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        secret_key="a-production-secret-that-is-long-enough",
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
        Settings(_env_file=None, app_env="production", secret_key=secret_key)


def test_non_production_environment_keeps_development_secret_compatibility() -> None:
    assert Settings(_env_file=None, app_env="development").secret_key == "replace-with-local-dev-secret"
    assert Settings(_env_file=None, app_env="test").secret_key == "replace-with-local-dev-secret"
