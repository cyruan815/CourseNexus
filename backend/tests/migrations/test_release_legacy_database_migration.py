from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LEGACY_FIXTURE = BACKEND_ROOT / "tests" / "fixtures" / "legacy-v1-release.sql"


def _alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


def _open_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_upgrade_preserves_realistic_legacy_material_citation_and_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "legacy-release.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()
    try:
        command.upgrade(_alembic_config(), "20260930_0006")
        with _open_database(database_path) as connection:
            connection.executescript(LEGACY_FIXTURE.read_text(encoding="utf-8"))
            assert connection.execute("SELECT COUNT(*) FROM material_chunks").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM source_citations").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM study_subtasks").fetchone()[0] == 2

        get_settings.cache_clear()
        command.upgrade(_alembic_config(), "head")

        with _open_database(database_path) as connection:
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20261001_0008"
            material = connection.execute(
                "SELECT parse_status, active_parse_version_id FROM course_materials "
                "WHERE id = 'mat_release_legacy'"
            ).fetchone()
            assert material["parse_status"] == "parsed"
            assert material["active_parse_version_id"]

            version = connection.execute(
                "SELECT id, status, parse_quality, page_count FROM material_parse_versions "
                "WHERE material_id = 'mat_release_legacy'"
            ).fetchone()
            assert dict(version) == {
                "id": material["active_parse_version_id"],
                "status": "active",
                "parse_quality": "complete",
                "page_count": 1,
            }
            assert connection.execute(
                "SELECT parse_version_id FROM material_chunks WHERE id = 'chk_release_legacy'"
            ).fetchone()[0] == version["id"]
            assert connection.execute(
                "SELECT material_version_id FROM source_citations WHERE id = 'cite_release_legacy'"
            ).fetchone()[0] == version["id"]

            plan = connection.execute(
                "SELECT title, goal_text, parsed_config_json, status FROM study_plans "
                "WHERE id = 'sp_release_legacy'"
            ).fetchone()
            assert plan["title"] == "Limits Review 2026-10-01"
            assert plan["goal_text"] == "Review limits and continuity"
            assert plan["status"] == "active"
            assert json.loads(plan["parsed_config_json"])["material_scope"]["material_ids"] == [
                "mat_release_legacy"
            ]
            assert connection.execute(
                "SELECT title FROM study_tasks WHERE id = 'task_release_legacy'"
            ).fetchone()[0] == "Limits and continuity review"
            assert [
                row[0]
                for row in connection.execute(
                    "SELECT subtask_type FROM study_subtasks "
                    "WHERE plan_id = 'sp_release_legacy' ORDER BY sort_order"
                ).fetchall()
            ] == ["learn", "test"]
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        get_settings.cache_clear()
