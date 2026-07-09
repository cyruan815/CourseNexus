from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./course_nexus.db"
    app_env: str = "development"
    secret_key: str = "replace-with-local-dev-secret"
    access_token_expire_minutes: int = 1440
    file_storage_path: str = "./uploads"
    max_upload_file_size_bytes: int = 52_428_800
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    model_api_base_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
