from __future__ import annotations

import pytest

import app.api.dependencies as dependencies
from app.api.dependencies import get_retrieval_rag_index
from app.core.config import Settings
from app.core.errors import CourseNexusError


def test_retrieval_rag_dependency_reports_retrieval_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "get_settings", lambda: Settings(_env_file=None, openai_api_key=None))

    with pytest.raises(CourseNexusError) as exc_info:
        get_retrieval_rag_index()

    assert exc_info.value.code == "RETRIEVAL_FAILED"
