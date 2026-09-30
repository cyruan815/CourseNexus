from __future__ import annotations

import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def test_upgrade_backfills_versions_chunks_and_citations(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        command.upgrade(_alembic_config(), "20260930_0006")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, username, password_hash) "
                    "VALUES ('usr_legacy', 'legacy', 'hash')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO courses (id, user_id, name) "
                    "VALUES ('crs_legacy', 'usr_legacy', 'Legacy Course')"
                )
            )
            material_values = [
                {
                    "id": "mat_good",
                    "name": "good.txt",
                    "parse_status": "parsed",
                    "parse_error": None,
                    "parse_quality": "complete",
                    "diagnostics": json.dumps({"parser": "legacy"}),
                    "page_count": 1,
                },
                {
                    "id": "mat_empty",
                    "name": "empty.txt",
                    "parse_status": "parsed",
                    "parse_error": None,
                    "parse_quality": "complete",
                    "diagnostics": json.dumps({"parser": "legacy"}),
                    "page_count": 2,
                },
                {
                    "id": "mat_failed",
                    "name": "failed.txt",
                    "parse_status": "parse_failed",
                    "parse_error": "OLD_FAILURE",
                    "parse_quality": "unknown",
                    "diagnostics": None,
                    "page_count": None,
                },
            ]
            connection.execute(
                text(
                    "INSERT INTO course_materials "
                    "(id, course_id, user_id, name, material_type, source_type, file_url, "
                    "parse_status, parse_error, parse_quality, parse_diagnostics_json, page_count) "
                    "VALUES (:id, 'crs_legacy', 'usr_legacy', :name, 'text', 'file', :name, "
                    ":parse_status, :parse_error, :parse_quality, :diagnostics, :page_count)"
                ),
                material_values,
            )
            connection.execute(
                text(
                    "INSERT INTO material_chunks "
                    "(id, material_id, course_id, chunk_index, page, page_index, content_text) "
                    "VALUES ('chk_legacy', 'mat_good', 'crs_legacy', 0, '1', 0, 'legacy text')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO conversations (id, user_id, course_id, title) "
                    "VALUES ('conv_legacy', 'usr_legacy', 'crs_legacy', 'Legacy')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO messages (id, conversation_id, course_id, role, content) "
                    "VALUES ('msg_legacy', 'conv_legacy', 'crs_legacy', 'assistant', 'answer')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO source_citations "
                    "(id, message_id, material_id, chunk_id, material_name, page, hit_text) "
                    "VALUES ('cite_legacy', 'msg_legacy', 'mat_good', 'chk_legacy', 'good.txt', '1', 'legacy')"
                )
            )
        engine.dispose()

        get_settings.cache_clear()
        command.upgrade(_alembic_config(), "head")

        engine = create_engine(database_url)
        with engine.connect() as connection:
            good = connection.execute(
                text(
                    "SELECT parse_status, active_parse_version_id FROM course_materials "
                    "WHERE id = 'mat_good'"
                )
            ).mappings().one()
            good_version = connection.execute(
                text(
                    "SELECT id, status, parse_quality FROM material_parse_versions "
                    "WHERE material_id = 'mat_good'"
                )
            ).mappings().one()
            assert good["parse_status"] == "parsed"
            assert good["active_parse_version_id"] == good_version["id"]
            assert good_version["status"] == "active"
            assert good_version["parse_quality"] == "complete"
            assert connection.execute(
                text("SELECT parse_version_id FROM material_chunks WHERE id = 'chk_legacy'")
            ).scalar_one() == good_version["id"]
            assert connection.execute(
                text("SELECT material_version_id FROM source_citations WHERE id = 'cite_legacy'")
            ).scalar_one() == good_version["id"]

            empty = connection.execute(
                text(
                    "SELECT parse_status, parse_error, active_parse_version_id "
                    "FROM course_materials WHERE id = 'mat_empty'"
                )
            ).mappings().one()
            assert empty == {
                "parse_status": "parse_failed",
                "parse_error": "MIGRATION_EMPTY_PARSE",
                "active_parse_version_id": None,
            }
            assert connection.execute(
                text("SELECT status FROM material_parse_versions WHERE material_id = 'mat_empty'")
            ).scalar_one() == "failed"
            assert connection.execute(
                text("SELECT parse_error FROM material_parse_versions WHERE material_id = 'mat_failed'")
            ).scalar_one() == "OLD_FAILURE"
        engine.dispose()

        get_settings.cache_clear()
        command.downgrade(_alembic_config(), "20260930_0006")
        engine = create_engine(database_url)
        inspector = inspect(engine)
        assert "material_parse_versions" not in inspector.get_table_names()
        assert "parse_version_id" not in {column["name"] for column in inspector.get_columns("material_chunks")}
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT material_id FROM material_chunks WHERE id = 'chk_legacy'")
            ).scalar_one() == "mat_good"
        engine.dispose()
    finally:
        get_settings.cache_clear()
