from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from threading import Lock

from app.core.config import Settings, get_settings
from app.core.errors import CourseNexusError
from app.integrations.rag.base import RagIndex


RagIndexFactory = Callable[[Settings], RagIndex]


class RagIndexManager:
    def __init__(
        self,
        *,
        settings_provider: Callable[[], Settings] = get_settings,
        index_factory: RagIndexFactory | None = None,
    ) -> None:
        self._settings_provider = settings_provider
        self._index_factory = index_factory or _create_configured_index
        self._index: RagIndex | None = None
        self._lock = Lock()

    def initialize(self) -> RagIndex | None:
        if self._index is not None:
            return self._index
        settings = self._settings_provider()
        if not (settings.model_endpoint("embedding").api_key or "").strip():
            return None
        with self._lock:
            if self._index is None:
                self._index = self._index_factory(settings)
            return self._index

    def require_index(self, *, missing_code: str, missing_message: str) -> RagIndex:
        index = self.initialize()
        if index is None:
            raise CourseNexusError(
                code=missing_code,
                message=missing_message,
                status_code=502,
            )
        return index

    def close(self) -> None:
        with self._lock:
            self._index = None

    @property
    def is_initialized(self) -> bool:
        return self._index is not None


def _create_configured_index(settings: Settings) -> RagIndex:
    from app.integrations.rag.llama_index_chroma import create_openai_chroma_rag_index

    endpoint = settings.model_endpoint("embedding")
    return create_openai_chroma_rag_index(
        persist_path=settings.chroma_persist_path,
        collection_name=settings.chroma_collection,
        api_key=endpoint.api_key or "",
        embedding_model=endpoint.model,
        api_base_url=endpoint.base_url,
    )


@lru_cache
def get_rag_index_manager() -> RagIndexManager:
    return RagIndexManager()
