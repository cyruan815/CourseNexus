from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app.core.config import Settings
from app.core.errors import CourseNexusError
from app.integrations.rag.fake import FakeRagIndex
from app.integrations.rag.manager import RagIndexManager


def test_manager_creates_only_one_process_index_instance() -> None:
    created: list[FakeRagIndex] = []

    def create_index(_settings: Settings) -> FakeRagIndex:
        index = FakeRagIndex()
        created.append(index)
        return index

    manager = RagIndexManager(
        settings_provider=lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
        ),
        index_factory=create_index,
    )

    first = manager.require_index(missing_code="INDEXING_FAILED", missing_message="missing")
    second = manager.require_index(missing_code="RETRIEVAL_FAILED", missing_message="missing")

    assert first is second
    assert created == [first]
    assert manager.is_initialized is True


def test_manager_reports_consumer_specific_missing_configuration() -> None:
    manager = RagIndexManager(
        settings_provider=lambda: Settings(_env_file=None),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        manager.require_index(
            missing_code="RETRIEVAL_FAILED",
            missing_message="资料检索配置缺失",
        )

    assert exc_info.value.code == "RETRIEVAL_FAILED"
    assert exc_info.value.status_code == 502
    assert manager.is_initialized is False


def test_manager_close_releases_reference_without_clearing_index() -> None:
    indexes = [FakeRagIndex(), FakeRagIndex()]
    manager = RagIndexManager(
        settings_provider=lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
        ),
        index_factory=lambda _settings: indexes.pop(0),
    )
    first = manager.initialize()

    manager.close()
    second = manager.initialize()

    assert first is not second
    assert manager.is_initialized is True


def test_concurrent_callers_share_one_index_instance() -> None:
    created: list[FakeRagIndex] = []
    barrier = Barrier(8)

    def create_index(_settings: Settings) -> FakeRagIndex:
        index = FakeRagIndex()
        created.append(index)
        return index

    manager = RagIndexManager(
        settings_provider=lambda: Settings(
            _env_file=None,
            embedding_api_key="embedding-key",
        ),
        index_factory=create_index,
    )

    def initialize_after_barrier() -> object:
        barrier.wait()
        return manager.initialize()

    with ThreadPoolExecutor(max_workers=8) as executor:
        indexes = list(executor.map(lambda _index: initialize_after_barrier(), range(8)))

    assert len(created) == 1
    assert all(index is created[0] for index in indexes)
