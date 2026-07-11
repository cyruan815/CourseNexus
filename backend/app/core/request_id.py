from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.logging import bind_request_id, get_logger, reset_request_id


REQUEST_ID_HEADER = "X-Request-ID"
logger = get_logger("http.request")


def generate_request_id() -> str:
    return f"req_{uuid4().hex}"


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return generate_request_id()


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, slow_request_ms: int = 3_000) -> None:
        super().__init__(app)
        self.slow_request_ms = slow_request_ms

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get(REQUEST_ID_HEADER) or generate_request_id()
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        started_at = perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                cost_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.error(
                    "%s %s -> 500 | method=%s path=%s status=500 cost_ms=%.2f",
                    request.method,
                    request.url.path,
                    request.method,
                    request.url.path,
                    cost_ms,
                )
                raise
            response.headers[REQUEST_ID_HEADER] = request_id
            cost_ms = round((perf_counter() - started_at) * 1000, 2)
            message = (
                f"{request.method} {request.url.path} -> {response.status_code}"
                f" | method={request.method} path={request.url.path}"
                f" status={response.status_code} cost_ms={cost_ms}"
            )
            if response.status_code >= 500:
                logger.error(message)
            elif cost_ms >= self.slow_request_ms:
                logger.warning(f"请求较慢 | {message}")
            else:
                logger.info(message)
            return response
        finally:
            reset_request_id(token)
