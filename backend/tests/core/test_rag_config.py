from app.core.config import Settings


def test_openai_settings_include_embedding_model() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_embedding_model == "text-embedding-3-small"
