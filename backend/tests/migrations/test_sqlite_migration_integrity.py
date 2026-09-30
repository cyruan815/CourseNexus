from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def test_batch_migration_preserves_referenced_sqlite_rows(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "referenced.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        command.upgrade(_alembic_config(), "20260709_0001")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, username, password_hash) "
                    "VALUES ('usr_migration', 'migration', 'hash')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO courses (id, user_id, name) "
                    "VALUES ('crs_migration', 'usr_migration', 'Migration Course')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO course_materials "
                    "(id, course_id, user_id, name, material_type, source_type, file_url, parse_status) "
                    "VALUES ('mat_migration', 'crs_migration', 'usr_migration', 'migration.txt', "
                    "'text', 'file', 'migration.txt', 'parsed')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO material_chunks "
                    "(id, material_id, course_id, chunk_index, page, content_text) "
                    "VALUES ('chk_migration', 'mat_migration', 'crs_migration', 0, '1', 'content')"
                )
            )
        engine.dispose()

        get_settings.cache_clear()
        application_logger = logging.getLogger("course_nexus.migration-test")
        application_logger.disabled = False
        command.upgrade(_alembic_config(), "20260712_0002")
        assert application_logger.disabled is False

        engine = create_engine(database_url)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT material_id FROM material_chunks WHERE id = 'chk_migration'")
            ).scalar_one() == "mat_migration"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        engine.dispose()
    finally:
        get_settings.cache_clear()
