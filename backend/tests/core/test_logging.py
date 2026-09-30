from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from sqlalchemy.exc import OperationalError as SqlAlchemyOperationalError

from app.core.config import Settings
from app.core.logging import (
    CompactConsoleFormatter,
    RequestContextFilter,
    UvicornRequestExceptionFilter,
    bind_request_id,
    configure_logging,
    exception_summary,
    get_logger,
    reset_request_id,
)


def test_exception_summary_preserves_original_type_and_message() -> None:
    assert exception_summary(TimeoutError("request timed out")) == "TimeoutError: request timed out"


def test_exception_summary_uses_database_driver_root_cause() -> None:
    error = SqlAlchemyOperationalError(
        "select missing_column from study_plans",
        {},
        sqlite3.OperationalError("no such column: study_plans.missing_column"),
    )

    assert exception_summary(error) == "OperationalError: no such column: study_plans.missing_column"


def test_compact_console_formatter_colors_level_and_event() -> None:
    record = logging.LogRecord(
        name="course_nexus.api.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="请求失败",
        args=(),
        exc_info=None,
    )
    RequestContextFilter().filter(record)
    formatter = CompactConsoleFormatter(
        "%(levelname)s | %(event_name)s | %(message)s",
        use_colors=True,
    )

    output = formatter.format(record)

    assert "\x1b[31mERROR\x1b[0m" in output
    assert "\x1b[31mapi.error\x1b[0m" in output


def test_uvicorn_request_exception_filter_only_drops_duplicate_asgi_traceback() -> None:
    duplicate = logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Exception in ASGI application\n",
        args=(),
        exc_info=(RuntimeError, RuntimeError("boom"), None),
    )
    startup = logging.LogRecord(
        name="uvicorn.error",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Application startup complete.",
        args=(),
        exc_info=None,
    )
    log_filter = UvicornRequestExceptionFilter()

    assert log_filter.filter(duplicate) is False
    assert log_filter.filter(startup) is True


def test_configure_logging_writes_compact_console_and_detailed_file(
    tmp_path: Path,
    capsys,
) -> None:
    settings = Settings(
        log_dir=str(tmp_path),
        log_level="INFO",
        log_max_bytes=1024,
        log_backup_count=2,
    )
    configure_logging(settings)
    logger = get_logger("materials.parse")
    token = bind_request_id("req_test")
    try:
        try:
            raise ValueError("broken document")
        except ValueError:
            logger.exception("解析失败 | material=mat_1")
    finally:
        reset_request_id(token)

    for handler in logging.getLogger("course_nexus").handlers:
        handler.flush()
    console = capsys.readouterr().err
    file_text = (tmp_path / "course-nexus.log").read_text(encoding="utf-8")
    expected = "ERROR | materials.parse | 解析失败 | material=mat_1 | req=req_test"
    assert expected in console
    assert "+08:00 | ERROR" in console
    assert "Traceback" not in console
    assert "error=ValueError: broken document" in console
    assert expected in file_text
    assert "Traceback" in file_text
    assert "ValueError: broken document" in file_text


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    settings = Settings(log_dir=str(tmp_path))
    configure_logging(settings)
    configure_logging(settings)

    assert len(logging.getLogger("course_nexus").handlers) == 2
    assert sum(
        isinstance(log_filter, UvicornRequestExceptionFilter)
        for log_filter in logging.getLogger("uvicorn.error").filters
    ) == 1


def test_configure_logging_redacts_message_arguments_and_exceptions(
    tmp_path: Path,
    capsys,
) -> None:
    settings = Settings(
        _env_file=None,
        log_dir=str(tmp_path),
        secret_key="runtime-secret-value",
        course_qa_api_key="runtime-api-key",
    )
    configure_logging(settings)
    logger = get_logger("model.security")
    try:
        raise RuntimeError(
            "provider rejected runtime-secret-value and runtime-api-key"
        )
    except RuntimeError:
        logger.exception(
            "调用失败 | api_key=%s authorization=Bearer %s",
            "runtime-api-key",
            "runtime-bearer-token",
        )

    for handler in logging.getLogger("course_nexus").handlers:
        handler.flush()
    console = capsys.readouterr().err
    file_text = (tmp_path / "course-nexus.log").read_text(encoding="utf-8")

    for output in (console, file_text):
        assert "runtime-secret-value" not in output
        assert "runtime-api-key" not in output
        assert "runtime-bearer-token" not in output
        assert "[REDACTED]" in output
