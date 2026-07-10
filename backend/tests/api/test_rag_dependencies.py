from __future__ import annotations

import pytest

import app.api.dependencies as dependencies
import app.integrations.rag.llama_index_chroma as llama_index_chroma
from app.api.dependencies import get_rag_index, get_retrieval_rag_index
from app.core.config import Settings
from app.core.errors import CourseNexusError


def test_retrieval_rag_dependency_reports_retrieval_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "get_settings", lambda: Settings(_env_file=None, embedding_api_key=None))

    with pytest.raises(CourseNexusError) as exc_info:
        get_retrieval_rag_index()

    assert exc_info.value.code == "RETRIEVAL_FAILED"


def test_rag_dependency_passes_embedding_endpoint_to_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_openai_chroma_rag_index(
        *,
        persist_path: str,
        collection_name: str,
        api_key: str,
        embedding_model: str,
        api_base_url: str | None,
    ):
        captured.update(
            persist_path=persist_path,
            collection_name=collection_name,
            api_key=api_key,
            embedding_model=embedding_model,
            api_base_url=api_base_url,
        )
        return object()

    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
            embedding_model="text-embedding-3-large",
            embedding_base_url="https://embedding.example/v1",
        ),
    )
    monkeypatch.setattr(llama_index_chroma, "create_openai_chroma_rag_index", fake_create_openai_chroma_rag_index)

    rag_index = get_rag_index()

    assert rag_index is not None
    assert captured == {
        "persist_path": "./data/chroma",
        "collection_name": "course_nexus_material_chunks",
        "api_key": "embedding-key",
        "embedding_model": "text-embedding-3-large",
        "api_base_url": "https://embedding.example/v1",
    }
