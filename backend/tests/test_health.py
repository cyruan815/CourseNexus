from fastapi.testclient import TestClient

import app.api.router as api_router_module
from app.core.config import Settings
from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {
        "status": "ok",
        "environment": "development",
        "mock_model_provider_enabled": False,
    }
    assert body["meta"]["api_version"] == "v1"
    assert body["meta"]["request_id"].startswith("req_")
    assert "server_time" in body["meta"]


def test_health_endpoint_exposes_mock_mode_without_sensitive_configuration(monkeypatch) -> None:
    monkeypatch.setattr(
        api_router_module,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            app_env="test",
            enable_mock_model_provider=True,
            secret_key="do-not-return-this-secret",
            course_qa_api_key="do-not-return-this-key",
            course_qa_base_url="https://private-model.example/v1",
        ),
    )

    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "status": "ok",
        "environment": "test",
        "mock_model_provider_enabled": True,
    }
    serialized = response.text
    assert "do-not-return-this" not in serialized
    assert "private-model.example" not in serialized
