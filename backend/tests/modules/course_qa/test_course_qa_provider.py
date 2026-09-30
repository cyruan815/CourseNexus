from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import app.integrations.model_provider.factory as provider_factory
import app.modules.course_qa.router as course_qa_router
from app.core.config import Settings
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware


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


def test_unconfigured_course_qa_provider_returns_stable_503_error(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_factory,
        "get_settings",
        lambda: Settings(_env_file=None, enable_mock_model_provider=False),
    )
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/provider-probe")
    def provider_probe(provider=Depends(course_qa_router.get_model_provider)) -> dict[str, bool]:
        return {"configured": provider is not None}

    response = TestClient(app).get(
        "/provider-probe",
        headers={"X-Request-ID": "req_model_missing"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "MODEL_PROVIDER_NOT_CONFIGURED",
            "message": "模型服务未配置",
            "details": {"purpose": "course_qa"},
        },
        "meta": {"request_id": "req_model_missing"},
    }
