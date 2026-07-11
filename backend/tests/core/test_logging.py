from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings
from app.core.logging import (
    bind_request_id,
    configure_logging,
    exception_summary,
    get_logger,
    reset_request_id,
)


def test_exception_summary_preserves_original_type_and_message() -> None:
    assert exception_summary(TimeoutError("request timed out")) == "TimeoutError: request timed out"


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
