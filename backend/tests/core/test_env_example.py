import re
from pathlib import Path

from app.core.config import MODEL_PURPOSES


ROOT_DIR = Path(__file__).resolve().parents[3]


def test_env_example_declares_independent_endpoint_for_every_model_purpose() -> None:
    content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    for purpose in MODEL_PURPOSES:
        prefix = purpose.upper()
        assert f"{prefix}_API_KEY=" in content
        assert f"{prefix}_BASE_URL=" in content
        assert f"{prefix}_MODEL=" in content


def test_env_example_does_not_advertise_deprecated_shared_model_settings() -> None:
    content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY=" not in content
    assert "OPENAI_MODEL=" not in content
    assert "OPENAI_EMBEDDING_MODEL=" not in content
    assert "MODEL_API_BASE_URL=" not in content
    assert "# ==================== Embedding 向量模型 ====================" in content
    assert "# ==================== 课程智能体问答模型 ====================" in content


def test_env_example_documents_study_plan_api_styles_and_map_concurrency() -> None:
    content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    assert "STUDY_PLAN_GENERATOR_API_STYLE=auto" in content
    assert "STUDY_PLAN_MAP_API_STYLE=auto" in content
    assert "STUDY_PLAN_MAP_CONCURRENCY=1" in content
    assert "STUDY_PLAN_GENERATOR_BASE_URL=https://api.deepseek.com" in content
    assert "STUDY_PLAN_MAP_BASE_URL=https://api.deepseek.com" in content


def test_env_example_disables_mock_model_provider_by_default() -> None:
    content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    assert "APP_ENV=development" in content
    assert "ENABLE_MOCK_MODEL_PROVIDER=false" in content
    assert "production 必须使用至少 32 位的非默认 SECRET_KEY" in content


def test_env_example_keeps_verified_provider_defaults_without_secrets() -> None:
    content = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")

    assert "EMBEDDING_BASE_URL=https://aihubmix.com/v1" in content
    assert "EMBEDDING_MODEL=text-embedding-3-large" in content
    for purpose in MODEL_PURPOSES:
        if purpose == "embedding":
            continue
        prefix = purpose.upper()
        assert f"{prefix}_BASE_URL=https://api.deepseek.com" in content
        assert f"{prefix}_MODEL=deepseek-flash" in content
    assert not re.search(r"^[A-Z0-9_]+_API_KEY=.+$", content, re.MULTILINE)
