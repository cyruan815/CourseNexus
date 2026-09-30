from __future__ import annotations

import pytest

import app.api.dependencies as dependencies
from app.api.dependencies import get_rag_index, get_retrieval_rag_index
from app.core.errors import CourseNexusError


def test_retrieval_rag_dependency_reports_retrieval_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingManager:
        def require_index(self, *, missing_code: str, missing_message: str):
            raise CourseNexusError(
                code=missing_code,
                message=missing_message,
                status_code=502,
            )

    monkeypatch.setattr(dependencies, "get_rag_index_manager", lambda: MissingManager())

    with pytest.raises(CourseNexusError) as exc_info:
        get_retrieval_rag_index()

    assert exc_info.value.code == "RETRIEVAL_FAILED"


def test_rag_dependencies_request_consumer_specific_error_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    expected_index = object()

    class RecordingManager:
        def require_index(self, *, missing_code: str, missing_message: str):
            captured[missing_code] = missing_message
            return expected_index

    monkeypatch.setattr(
        dependencies,
        "get_rag_index_manager",
        lambda: RecordingManager(),
    )

    indexing_index = get_rag_index()
    retrieval_index = get_retrieval_rag_index()

    assert indexing_index is expected_index
    assert retrieval_index is expected_index
    assert captured == {
        "INDEXING_FAILED": "资料索引配置缺失",
        "RETRIEVAL_FAILED": "资料检索配置缺失",
    }
