from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == {"status": "ok"}
    assert body["meta"]["api_version"] == "v1"
    assert body["meta"]["request_id"].startswith("req_")
    assert "server_time" in body["meta"]
