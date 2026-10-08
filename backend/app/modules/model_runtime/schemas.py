from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import BaseModel, Field, SecretStr, field_validator


class ModelEndpointConfigUpdate(BaseModel):
    model: str = Field(min_length=1, max_length=255)
    base_url: str = Field(min_length=1, max_length=2048)
    api_key: SecretStr | None = Field(default=None, max_length=2048)

    @field_validator("model", "base_url")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        if "\n" in normalized or "\r" in normalized:
            raise ValueError("value must be a single line")
        return normalized

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("base_url must use a valid port") from exc
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or not parsed.hostname
            or any(character.isspace() for character in value)
        ):
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("base_url must not contain credentials")
        return value.rstrip("/")

    @field_validator("api_key", mode="before")
    @classmethod
    def normalize_api_key(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            return None
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            raise ValueError("api_key must not contain control characters")
        return normalized


class ModelRuntimeConfigUpdate(BaseModel):
    embedding: ModelEndpointConfigUpdate
    general: ModelEndpointConfigUpdate


class ModelEndpointConfigRead(BaseModel):
    model: str
    base_url: str | None
    api_key_configured: bool
    api_key_hint: str | None


class ModelRuntimeConfigRead(BaseModel):
    embedding: ModelEndpointConfigRead
    general: ModelEndpointConfigRead
    general_config_consistent: bool
