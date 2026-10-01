from __future__ import annotations

from contextvars import ContextVar, Token
from copy import copy
from datetime import datetime
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.redaction import SensitiveDataRedactor


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_FORMAT = "%(asctime)s | %(levelname)s | %(event_name)s | %(message)s | req=%(request_id)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_TIMEZONE = ZoneInfo("Asia/Shanghai")
_ANSI_RESET = "\x1b[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[36m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}
_MAX_EXCEPTION_SUMMARY_LENGTH = 500


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id.get() or "-"
        prefix = "course_nexus."
        record.event_name = record.name[len(prefix) :] if record.name.startswith(prefix) else record.name
        return True


def exception_summary(exc: BaseException | None) -> str | None:
    if exc is None:
        return None
    root_cause = _root_cause(exc)
    message = " ".join(str(root_cause).split())
    summary = f"{type(root_cause).__name__}: {message}" if message else type(root_cause).__name__
    if len(summary) > _MAX_EXCEPTION_SUMMARY_LENGTH:
        return f"{summary[: _MAX_EXCEPTION_SUMMARY_LENGTH - 1]}…"
    return summary


def _root_cause(exc: BaseException) -> BaseException:
    current = exc
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        original = getattr(current, "orig", None)
        next_error = original if isinstance(original, BaseException) else current.__cause__ or current.__context__
        if not isinstance(next_error, BaseException):
            break
        current = next_error
    return current


def _stream_supports_color(stream: object) -> bool:
    if "NO_COLOR" in os.environ or os.environ.get("TERM", "").lower() == "dumb":
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


class TimezoneFormatter(logging.Formatter):
    def __init__(
        self,
        *args: Any,
        redactor: SensitiveDataRedactor | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.redactor = redactor

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        timestamp = datetime.fromtimestamp(record.created, _LOG_TIMEZONE)
        return timestamp.isoformat(sep=" ", timespec="seconds")

    def redact(self, output: str) -> str:
        return self.redactor.redact(output) if self.redactor else output


class ExceptionSummaryFormatter(TimezoneFormatter):
    def format(self, record: logging.LogRecord) -> str:
        headline_record = copy(record)
        headline_record.exc_info = None
        headline_record.exc_text = None
        headline_record.stack_info = None
        headline = logging.Formatter.format(self, headline_record)
        summary = exception_summary(record.exc_info[1]) if record.exc_info else None
        if summary:
            headline = f"{headline} | error={summary}"
        if record.exc_info:
            return self.redact(f"{headline}\n{self.formatException(record.exc_info)}")
        return self.redact(headline)


class CompactConsoleFormatter(ExceptionSummaryFormatter):
    def __init__(self, *args: Any, use_colors: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        compact = copy(record)
        summary = exception_summary(record.exc_info[1]) if record.exc_info else None
        compact.exc_info = None
        compact.exc_text = None
        compact.stack_info = None
        if self.use_colors:
            color = _LEVEL_COLORS.get(record.levelno)
            if color:
                compact.levelname = f"{color}{record.levelname}{_ANSI_RESET}"
                compact.event_name = f"{color}{record.event_name}{_ANSI_RESET}"
        headline = logging.Formatter.format(self, compact)
        output = f"{headline} | error={summary}" if summary else headline
        return self.redact(output)


class UvicornRequestExceptionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.exc_info is not None
            and record.getMessage().strip().startswith("Exception in ASGI application")
        )


def configure_logging(settings: Settings) -> None:
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("course_nexus")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(settings.log_level)
    logger.propagate = False

    context_filter = RequestContextFilter()
    redactor = SensitiveDataRedactor(settings)
    console = logging.StreamHandler()
    console.addFilter(context_filter)
    console.setFormatter(
        CompactConsoleFormatter(
            _FORMAT,
            _DATE_FORMAT,
            redactor=redactor,
            use_colors=_stream_supports_color(console.stream),
        )
    )

    file_handler = RotatingFileHandler(
        log_dir / "course-nexus.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.addFilter(context_filter)
    file_handler.setFormatter(
        ExceptionSummaryFormatter(_FORMAT, _DATE_FORMAT, redactor=redactor)
    )

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    for log_filter in uvicorn_error_logger.filters[:]:
        if isinstance(log_filter, UvicornRequestExceptionFilter):
            uvicorn_error_logger.removeFilter(log_filter)
    uvicorn_error_logger.addFilter(UvicornRequestExceptionFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"course_nexus.{name}")


def bind_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)
