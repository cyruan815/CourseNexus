from __future__ import annotations

from contextvars import ContextVar, Token
from copy import copy
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

from app.core.config import Settings


_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_FORMAT = "%(asctime)s | %(levelname)s | %(event_name)s | %(message)s | req=%(request_id)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_TIMEZONE = ZoneInfo("Asia/Shanghai")


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
    message = str(exc).replace("\n", " ").strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


class TimezoneFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        timestamp = datetime.fromtimestamp(record.created, _LOG_TIMEZONE)
        return timestamp.isoformat(sep=" ", timespec="seconds")


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
            return f"{headline}\n{self.formatException(record.exc_info)}"
        return headline


class CompactConsoleFormatter(ExceptionSummaryFormatter):
    def format(self, record: logging.LogRecord) -> str:
        compact = copy(record)
        summary = exception_summary(record.exc_info[1]) if record.exc_info else None
        compact.exc_info = None
        compact.exc_text = None
        compact.stack_info = None
        headline = logging.Formatter.format(self, compact)
        return f"{headline} | error={summary}" if summary else headline


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
    console = logging.StreamHandler()
    console.addFilter(context_filter)
    console.setFormatter(CompactConsoleFormatter(_FORMAT, _DATE_FORMAT))

    file_handler = RotatingFileHandler(
        log_dir / "course-nexus.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.addFilter(context_filter)
    file_handler.setFormatter(ExceptionSummaryFormatter(_FORMAT, _DATE_FORMAT))

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"course_nexus.{name}")


def bind_request_id(request_id: str) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)
