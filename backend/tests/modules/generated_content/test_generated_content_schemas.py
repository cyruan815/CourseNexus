from datetime import datetime, timezone

from app.modules.generated_content.schemas import GeneratedContentRead


def _generated_content_read(*, created_at: datetime, updated_at: datetime) -> GeneratedContentRead:
    return GeneratedContentRead(
        id="gen_1",
        user_id="usr_1",
        course_id="crs_1",
        study_subtask_id=None,
        source_message_id=None,
        content_type="flashcard",
        title="知识闪卡",
        content=None,
        content_json={"cards": []},
        generation_status="success",
        material_scope_json=None,
        error_code=None,
        created_at=created_at,
        updated_at=updated_at,
        deleted_at=None,
    )


def test_generated_content_serializes_naive_sqlite_timestamps_as_beijing_time() -> None:
    content = _generated_content_read(
        created_at=datetime(2026, 7, 15, 14, 18, 10),
        updated_at=datetime(2026, 7, 15, 14, 20, 0),
    )

    payload = content.model_dump(mode="json")

    assert payload["created_at"] == "2026-07-15T22:18:10+08:00"
    assert payload["updated_at"] == "2026-07-15T22:20:00+08:00"
    assert payload["deleted_at"] is None


def test_generated_content_converts_aware_utc_timestamps_to_beijing_time() -> None:
    content = _generated_content_read(
        created_at=datetime(2026, 7, 15, 14, 18, 10, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 15, 14, 20, 0, tzinfo=timezone.utc),
    )

    payload = content.model_dump(mode="json")

    assert payload["created_at"] == "2026-07-15T22:18:10+08:00"
    assert payload["updated_at"] == "2026-07-15T22:20:00+08:00"
