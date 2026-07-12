from sqlalchemy import create_engine, inspect

from app.db.base import Base
import app.db.models  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "courses",
    "material_folders",
    "course_materials",
    "material_chunks",
    "conversations",
    "messages",
    "source_citations",
    "ai_generated_contents",
    "study_plans",
    "study_tasks",
    "study_subtasks",
    "checkin_records",
}


def test_core_schema_creates_expected_tables() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES


def test_key_columns_are_present() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    columns_by_table = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in EXPECTED_TABLES
    }

    assert {"username", "password_hash", "status"} <= columns_by_table["users"]
    assert {"user_id", "name", "status", "deleted_at"} <= columns_by_table["courses"]
    assert {
        "parse_status",
        "parse_quality",
        "parse_diagnostics_json",
        "file_url",
        "source_url",
    } <= columns_by_table["course_materials"]
    assert {"message_id", "generated_content_id", "hit_text"} <= columns_by_table["source_citations"]
    assert {"content_type", "content_json", "study_subtask_id"} <= columns_by_table["ai_generated_contents"]
    assert {"task_date", "status", "sort_order"} <= columns_by_table["study_tasks"]
    assert {"subtask_type", "related_material_ids_json", "completed_at"} <= columns_by_table["study_subtasks"]
    assert {"checkin_date", "completion_ratio", "color_level"} <= columns_by_table["checkin_records"]


def test_material_parse_quality_is_required_with_unknown_default() -> None:
    table = Base.metadata.tables["course_materials"]
    parse_quality = table.columns["parse_quality"]

    assert parse_quality.nullable is False
    assert str(parse_quality.server_default.arg) == "unknown"


def test_source_citation_can_keep_snapshot_after_material_is_deleted() -> None:
    table = Base.metadata.tables["source_citations"]

    assert table.columns["material_id"].nullable is True
    assert table.columns["chunk_id"].nullable is True
