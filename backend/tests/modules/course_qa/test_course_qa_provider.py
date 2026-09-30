from __future__ import annotations

import app.modules.course_qa.router as course_qa_router


def test_course_qa_provider_uses_shared_factory(monkeypatch) -> None:
    captured: list[str] = []
    expected_provider = object()
    monkeypatch.setattr(
        course_qa_router,
        "create_model_provider",
        lambda purpose: captured.append(purpose) or expected_provider,
    )

    provider = course_qa_router.get_model_provider()

    assert provider is expected_provider
    assert captured == ["course_qa"]
