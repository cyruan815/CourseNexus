import logging

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from app.core.errors import CourseNexusError, register_exception_handlers
from app.core.logging import RequestContextFilter
from app.core.request_id import RequestIdMiddleware


def _start_capture(caplog) -> tuple[logging.Logger, RequestContextFilter]:
    logger = logging.getLogger("course_nexus")
    context_filter = RequestContextFilter()
    caplog.handler.addFilter(context_filter)
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger, context_filter


def _stop_capture(logger: logging.Logger, context_filter: RequestContextFilter, caplog) -> None:
    logger.removeHandler(caplog.handler)
    caplog.handler.removeFilter(context_filter)


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


def test_request_log_contains_status_cost_and_request_id(caplog) -> None:
    from app.main import app

    logger, context_filter = _start_capture(caplog)
    try:
        response = TestClient(app).get("/api/v1/health", headers={"X-Request-ID": "req_log"})
    finally:
        _stop_capture(logger, context_filter, caplog)

    assert response.status_code == 200
    record = next(record for record in caplog.records if record.name.endswith("http.request"))
    assert "GET /api/v1/health -> 200" in record.getMessage()
    assert "cost_ms=" in record.getMessage()
    assert record.request_id == "req_log"


def test_unexpected_error_logs_original_exception(caplog) -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware, slow_request_ms=3000)
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("database unavailable")

    logger, context_filter = _start_capture(caplog)
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/boom", headers={"X-Request-ID": "req_boom"}
        )
    finally:
        _stop_capture(logger, context_filter, caplog)

    assert response.status_code == 500
    record = next(record for record in caplog.records if record.name.endswith("api.error"))
    assert record.levelno == logging.ERROR
    assert record.exc_info is not None
    assert isinstance(record.exc_info[1], RuntimeError)
    assert record.request_id == "req_boom"


def test_not_found_is_logged_as_info(caplog) -> None:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/missing")
    def missing() -> None:
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)

    logger, context_filter = _start_capture(caplog)
    try:
        response = TestClient(app).get("/missing")
    finally:
        _stop_capture(logger, context_filter, caplog)

    assert response.status_code == 404
    error_record = next(record for record in caplog.records if record.name.endswith("api.error"))
    assert error_record.levelno == logging.INFO


def test_slow_request_is_logged_as_warning(caplog, monkeypatch) -> None:
    from app.core import request_id as request_id_module

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware, slow_request_ms=100)

    @app.get("/slow")
    def slow() -> dict[str, bool]:
        return {"ok": True}

    times = iter([1.0, 1.2])
    monkeypatch.setattr(request_id_module, "perf_counter", lambda: next(times))
    logger, context_filter = _start_capture(caplog)
    try:
        response = TestClient(app).get("/slow")
    finally:
        _stop_capture(logger, context_filter, caplog)

    assert response.status_code == 200
    record = next(record for record in caplog.records if record.name.endswith("http.request"))
    assert record.levelno == logging.WARNING
    assert "请求较慢" in record.getMessage()
    assert "cost_ms=200.0" in record.getMessage()
