from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_required_user
from app.main import app
from app.modules.model_runtime import router as model_runtime_router
from app.modules.model_runtime.schemas import ModelRuntimeConfigRead


def config_response() -> ModelRuntimeConfigRead:
    return ModelRuntimeConfigRead.model_validate(
        {
            "embedding": {
                "model": "embedding-model",
                "base_url": "https://embedding.example/v1",
                "api_key_configured": True,
                "api_key_hint": "embe••••",
            },
            "general": {
                "model": "general-model",
                "base_url": "https://models.example/v1",
                "api_key_configured": True,
                "api_key_hint": "gene••••",
            },
            "general_config_consistent": True,
        }
    )


def test_model_config_requires_authentication() -> None:
    app.dependency_overrides[get_current_user] = lambda: None
    try:
        response = TestClient(app).get("/api/v1/model-runtime/config")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_model_config_get_never_returns_complete_key(monkeypatch) -> None:
    app.dependency_overrides[get_required_user] = lambda: object()
    monkeypatch.setattr(
        model_runtime_router,
        "get_model_runtime_config",
        config_response,
    )
    try:
        response = TestClient(app).get("/api/v1/model-runtime/config")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["embedding"]["api_key_hint"] == "embe••••"
    assert "complete-secret" not in response.text


def test_model_config_put_accepts_two_groups(monkeypatch) -> None:
    captured = []
    app.dependency_overrides[get_required_user] = lambda: object()
    monkeypatch.setattr(
        model_runtime_router,
        "save_model_runtime_config",
        lambda payload: captured.append(payload) or config_response(),
    )
    try:
        response = TestClient(app).put(
            "/api/v1/model-runtime/config",
            json={
                "embedding": {
                    "model": "embedding-model",
                    "base_url": "https://embedding.example/v1",
                    "api_key": "embedding-complete-secret",
                },
                "general": {
                    "model": "general-model",
                    "base_url": "https://models.example/v1",
                    "api_key": "general-complete-secret",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].general.model == "general-model"
    assert "embedding-complete-secret" not in response.text
    assert "general-complete-secret" not in response.text


def test_model_config_validation_error_redacts_invalid_api_key() -> None:
    leaked_key = "secret-line-one\nsecret-line-two"
    app.dependency_overrides[get_required_user] = lambda: object()
    try:
        response = TestClient(app).put(
            "/api/v1/model-runtime/config",
            json={
                "embedding": {
                    "model": "embedding-model",
                    "base_url": "https://embedding.example/v1",
                    "api_key": leaked_key,
                },
                "general": {
                    "model": "general-model",
                    "base_url": "https://models.example/v1",
                    "api_key": "general-complete-secret",
                },
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert leaked_key not in response.text
    errors = response.json()["error"]["details"]["errors"]
    assert errors[0]["input"] == "[REDACTED]"
