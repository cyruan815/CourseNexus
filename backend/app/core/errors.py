from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_id import get_request_id
from app.core.logging import get_logger
from app.shared.responses import error_response


logger = get_logger("api.error")


class CourseNexusError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CourseNexusError)
    async def course_nexus_error_handler(request: Request, exc: CourseNexusError) -> JSONResponse:
        request_id = get_request_id(request)
        cause = exc.__cause__
        exc_info = (type(cause), cause, cause.__traceback__) if cause is not None else None
        logger.log(
            _business_error_level(exc.status_code),
            "请求失败：%s | code=%s method=%s path=%s",
            exc.message,
            exc.code,
            request.method,
            request.url.path,
            exc_info=exc_info,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = get_request_id(request)
        validation_errors = _serializable_validation_errors(exc)
        locations = [".".join(str(part) for part in error["loc"]) for error in validation_errors]
        logger.warning(
            "请求失败：请求参数不合法 | code=VALIDATION_ERROR method=%s path=%s fields=%s",
            request.method,
            request.url.path,
            ",".join(locations),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=422,
            content=error_response(
                code="VALIDATION_ERROR",
                message="请求参数不合法",
                details={"errors": validation_errors},
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = get_request_id(request)
        logger.error(
            "请求失败：服务端内部错误 | code=INTERNAL_ERROR method=%s path=%s",
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content=error_response(
                code="INTERNAL_ERROR",
                message="服务端内部错误",
                details={},
                request_id=request_id,
            ),
        )


def _serializable_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        cleaned = dict(error)
        ctx = cleaned.get("ctx")
        if isinstance(ctx, dict):
            cleaned["ctx"] = {key: str(value) for key, value in ctx.items()}
        errors.append(cleaned)
    return errors


def _business_error_level(status_code: int) -> int:
    if status_code in {401, 403, 404}:
        return logging.INFO
    if status_code >= 500:
        return logging.ERROR
    return logging.WARNING
