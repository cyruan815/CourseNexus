from app.core.config import Settings


def test_rag_settings_use_local_persistent_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.chroma_persist_path == "./data/chroma"
    assert settings.chroma_collection == "course_nexus_material_chunks"
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.rag_similarity_top_k == 8
    assert settings.rag_chunk_max_tokens == 800
    assert settings.material_batch_max_tokens == 12_000
