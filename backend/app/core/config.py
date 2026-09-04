from functools import lru_cache
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]

ModelPurpose = Literal[
    "embedding",
    "course_qa",
    "quiz",
    "flashcard",
    "mindmap",
    "outline",
    "knowledge_list",
    "study_plan_parser",
    "study_plan_diagnostic",
    "study_plan_generator",
    "handout",
    "task_test",
]
MODEL_PURPOSES: tuple[ModelPurpose, ...] = get_args(ModelPurpose)


class ModelEndpointConfig(BaseModel):
    api_key: str | None
    base_url: str | None
    model: str


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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_dir: str = "./logs"
    log_max_bytes: int = 20_971_520
    log_backup_count: int = 20
    slow_request_ms: int = 3_000
    cors_allowed_origins: str = "http://localhost:5173"

    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"

    course_qa_api_key: str | None = None
    course_qa_base_url: str | None = None
    course_qa_model: str = "gpt-5.4-mini"

    quiz_api_key: str | None = None
    quiz_base_url: str | None = None
    quiz_model: str = "gpt-5.4-mini"

    flashcard_api_key: str | None = None
    flashcard_base_url: str | None = None
    flashcard_model: str = "gpt-5.4-mini"

    mindmap_api_key: str | None = None
    mindmap_base_url: str | None = None
    mindmap_model: str = "gpt-5.4-mini"

    outline_api_key: str | None = None
    outline_base_url: str | None = None
    outline_model: str = "gpt-5.4-mini"

    knowledge_list_api_key: str | None = None
    knowledge_list_base_url: str | None = None
    knowledge_list_model: str = "gpt-5.4-mini"

    study_plan_parser_api_key: str | None = None
    study_plan_parser_base_url: str | None = None
    study_plan_parser_model: str = "gpt-5.4-mini"

    study_plan_diagnostic_api_key: str | None = None
    study_plan_diagnostic_base_url: str | None = None
    study_plan_diagnostic_model: str = "gpt-5.4-mini"

    study_plan_generator_api_key: str | None = None
    study_plan_generator_base_url: str | None = None
    study_plan_generator_model: str = "gpt-5.4-mini"
    study_plan_generator_api_style: Literal["auto", "responses", "chat"] = "auto"

    study_plan_map_api_key: str | None = None
    study_plan_map_base_url: str | None = None
    study_plan_map_model: str | None = None
    study_plan_map_api_style: Literal["auto", "responses", "chat"] = "auto"

    handout_api_key: str | None = None
    handout_base_url: str | None = None
    handout_model: str = "gpt-5.4-mini"

    task_test_api_key: str | None = None
    task_test_base_url: str | None = None
    task_test_model: str = "gpt-5.4-mini"

    # Deprecated compatibility fields. New .env files must use purpose-specific variables.
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_embedding_model: str | None = None
    model_api_base_url: str | None = None

    chroma_persist_path: str = "./data/chroma"
    chroma_collection: str = "course_nexus_material_chunks"
    rag_similarity_top_k: int = 8
    rag_chunk_max_tokens: int = 800
    material_batch_max_tokens: int = 12_000
    material_context_max_tokens: int = 120_000
    study_plan_map_concurrency: int = Field(default=1, ge=1, le=5)
    markmap_node_command: str = "node"
    markmap_transform_timeout_seconds: float = 15.0

    @model_validator(mode="after")
    def apply_legacy_model_settings(self) -> "Settings":
        configured_fields = self.model_fields_set

        if "embedding_api_key" not in configured_fields and self.openai_api_key:
            self.embedding_api_key = self.openai_api_key
        if "embedding_base_url" not in configured_fields and self.model_api_base_url:
            self.embedding_base_url = self.model_api_base_url
        if "embedding_model" not in configured_fields and self.openai_embedding_model:
            self.embedding_model = self.openai_embedding_model

        if "course_qa_api_key" not in configured_fields and self.openai_api_key:
            self.course_qa_api_key = self.openai_api_key
        if "course_qa_base_url" not in configured_fields and self.model_api_base_url:
            self.course_qa_base_url = self.model_api_base_url
        if "course_qa_model" not in configured_fields and self.openai_model:
            self.course_qa_model = self.openai_model

        return self

    def model_endpoint(self, purpose: ModelPurpose) -> ModelEndpointConfig:
        return ModelEndpointConfig(
            api_key=getattr(self, f"{purpose}_api_key") or None,
            base_url=getattr(self, f"{purpose}_base_url") or None,
            model=getattr(self, f"{purpose}_model"),
        )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
