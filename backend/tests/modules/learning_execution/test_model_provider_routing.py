from __future__ import annotations

import pytest

import app.modules.learning_execution.router as learning_router


@pytest.mark.parametrize(
    ("dependency", "purpose"),
    [
        (learning_router.get_handout_model_provider, "handout"),
        (learning_router.get_task_test_model_provider, "task_test"),
        (learning_router.get_task_qa_model_provider, "course_qa"),
    ],
)
def test_learning_execution_provider_uses_shared_factory(
    monkeypatch,
    dependency,
    purpose: str,
) -> None:
    captured: list[str] = []
    expected_provider = object()
    monkeypatch.setattr(
        learning_router,
        "create_model_provider",
        lambda requested_purpose: captured.append(requested_purpose) or expected_provider,
    )

    provider = dependency()

    assert provider is expected_provider
    assert captured == [purpose]
