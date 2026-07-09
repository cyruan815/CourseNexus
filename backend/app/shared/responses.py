from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def success_response(data: Any, request_id: str) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "request_id": request_id,
            "server_time": datetime.now(timezone.utc).isoformat(),
            "api_version": "v1",
        },
    }


def error_response(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "meta": {
            "request_id": request_id,
        },
    }
