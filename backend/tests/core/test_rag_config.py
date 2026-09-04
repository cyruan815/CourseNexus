import pytest
from pydantic import ValidationError

from app.core.config import MODEL_PURPOSES, Settings


def test_rag_settings_use_local_persistent_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.chroma_persist_path == "./data/chroma"
    assert settings.chroma_collection == "course_nexus_material_chunks"
    assert settings.model_endpoint("embedding").model == "text-embedding-3-small"
    assert settings.rag_similarity_top_k == 8
    assert settings.rag_chunk_max_tokens == 800
    assert settings.material_batch_max_tokens == 12_000
    assert settings.material_context_max_tokens == 120_000


def test_study_plan_map_concurrency_defaults_to_one_and_allows_up_to_five() -> None:
    assert Settings(_env_file=None).study_plan_map_concurrency == 1
    assert Settings(_env_file=None, study_plan_map_concurrency=5).study_plan_map_concurrency == 5

    with pytest.raises(ValidationError):
        Settings(_env_file=None, study_plan_map_concurrency=0)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, study_plan_map_concurrency=6)


def test_study_plan_provider_api_styles_default_to_auto_and_are_independent() -> None:
    defaults = Settings(_env_file=None)
    assert defaults.study_plan_generator_api_style == "auto"
    assert defaults.study_plan_map_api_style == "auto"

    configured = Settings(
        _env_file=None,
        study_plan_generator_api_style="responses",
        study_plan_map_api_style="chat",
    )
    assert configured.study_plan_generator_api_style == "responses"
    assert configured.study_plan_map_api_style == "chat"


def test_every_model_purpose_has_an_independent_endpoint() -> None:
    settings = Settings(
        _env_file=None,
        embedding_api_key="embedding-key",
        embedding_base_url="https://embedding.example/v1",
        embedding_model="embedding-model",
        course_qa_api_key="qa-key",
        course_qa_base_url="https://qa.example/v1",
        course_qa_model="qa-model",
        quiz_api_key="quiz-key",
        quiz_base_url="https://quiz.example/v1",
        quiz_model="quiz-model",
        study_plan_diagnostic_api_key="diagnostic-key",
        study_plan_diagnostic_base_url="https://diagnostic.example/v1",
        study_plan_diagnostic_model="diagnostic-model",
    )

    assert set(MODEL_PURPOSES) == {
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
    }
    assert settings.model_endpoint("embedding").model_dump() == {
        "api_key": "embedding-key",
        "base_url": "https://embedding.example/v1",
        "model": "embedding-model",
    }
    assert settings.model_endpoint("course_qa").model_dump() == {
        "api_key": "qa-key",
        "base_url": "https://qa.example/v1",
        "model": "qa-model",
    }
    assert settings.model_endpoint("quiz").model_dump() == {
        "api_key": "quiz-key",
        "base_url": "https://quiz.example/v1",
        "model": "quiz-model",
    }
    assert settings.model_endpoint("study_plan_diagnostic").model_dump() == {
        "api_key": "diagnostic-key",
        "base_url": "https://diagnostic.example/v1",
        "model": "diagnostic-model",
    }
    assert settings.model_endpoint("flashcard").api_key is None


def test_legacy_openai_settings_only_fall_back_for_existing_consumers() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="legacy-key",
        openai_model="legacy-chat",
        openai_embedding_model="legacy-embedding",
        model_api_base_url="https://legacy.example/v1",
    )

    assert settings.model_endpoint("embedding").model_dump() == {
        "api_key": "legacy-key",
        "base_url": "https://legacy.example/v1",
        "model": "legacy-embedding",
    }
    assert settings.model_endpoint("course_qa").model_dump() == {
        "api_key": "legacy-key",
        "base_url": "https://legacy.example/v1",
        "model": "legacy-chat",
    }
    assert settings.model_endpoint("quiz").api_key is None
