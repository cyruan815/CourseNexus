import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("app_env", ["development", "test", "production"])
def test_app_environment_accepts_supported_values(app_env: str) -> None:
    settings = Settings(_env_file=None, app_env=app_env)

    assert settings.app_env == app_env


def test_app_environment_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")
