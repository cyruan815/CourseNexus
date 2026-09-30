from __future__ import annotations

import pytest

import app.modules.generation.orchestrator.router as generation_router
from app.core.errors import CourseNexusError


def test_generation_provider_routes_content_type_to_shared_factory(monkeypatch) -> None:
    captured: list[str] = []
    expected_provider = object()
    monkeypatch.setattr(
        generation_router,
        "create_model_provider",
        lambda purpose: captured.append(purpose) or expected_provider,
    )

    provider = generation_router.get_generation_model_provider("outline")

    assert provider is expected_provider
    assert captured == ["outline"]


def test_generation_provider_rejects_unknown_purpose_before_factory(monkeypatch) -> None:
    monkeypatch.setattr(
        generation_router,
        "create_model_provider",
        lambda purpose: pytest.fail(f"unexpected factory call: {purpose}"),
    )

    with pytest.raises(CourseNexusError) as exc_info:
        generation_router.get_generation_model_provider("unsupported")

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.status_code == 422
