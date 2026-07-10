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
