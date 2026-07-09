from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from app.core.errors import CourseNexusError, register_exception_handlers
from app.core.request_id import RequestIdMiddleware


def test_health_response_uses_inbound_request_id() -> None:
    from app.main import app

    client = TestClient(app)

    response = client.get("/api/v1/health", headers={"X-Request-ID": "req_test"})

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["request_id"] == "req_test"


def test_course_nexus_error_uses_error_envelope() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise CourseNexusError(
            code="VALIDATION_ERROR",
            message="请求参数不合法",
            status_code=422,
            details={"field": "name"},
        )

    client = TestClient(app)

    response = client.get("/boom", headers={"X-Request-ID": "req_error"})

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "请求参数不合法",
            "details": {"field": "name"},
        },
        "meta": {"request_id": "req_error"},
    }


def test_validation_error_uses_error_envelope() -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/items")
    def read_items(limit: int = Query(...)) -> dict[str, int]:
        return {"limit": limit}

    client = TestClient(app)

    response = client.get("/items", headers={"X-Request-ID": "req_validation"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "请求参数不合法"
    assert "details" in body["error"]
    assert body["meta"]["request_id"] == "req_validation"
