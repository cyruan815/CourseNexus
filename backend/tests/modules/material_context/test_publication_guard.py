from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.material_context.service import assert_material_snapshot_publishable


def _snapshot(material_id: str, version_id: str) -> list[dict[str, str]]:
    return [{"material_id": material_id, "version_id": version_id}]


def test_publication_guard_accepts_existing_material_version(db: Session, context_seed) -> None:
    material = context_seed.math_material

    assert_material_snapshot_publishable(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_versions=_snapshot(material.id, material.active_parse_version_id),
    )


def test_publication_guard_rejects_deleted_material(db: Session, context_seed) -> None:
    material = context_seed.math_material
    version_id = material.active_parse_version_id
    material.deleted_at = datetime.now(timezone.utc)
    db.add(material)
    db.commit()

    with pytest.raises(CourseNexusError) as exc_info:
        assert_material_snapshot_publishable(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_versions=_snapshot(material.id, version_id),
        )

    assert exc_info.value.code == "MATERIAL_SCOPE_STALE"
    assert exc_info.value.details == {
        "expected_version_count": 1,
        "current_version_count": 0,
    }


def test_publication_guard_rejects_version_from_another_material(db: Session, context_seed) -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        assert_material_snapshot_publishable(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_versions=_snapshot(
                context_seed.math_material.id,
                context_seed.history_material.active_parse_version_id,
            ),
        )

    assert exc_info.value.code == "MATERIAL_SCOPE_STALE"


def test_publication_guard_rejects_course_owned_by_another_user(db: Session, context_seed) -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        assert_material_snapshot_publishable(
            db,
            user_id=context_seed.other_user.id,
            course_id=context_seed.course.id,
            material_versions=[],
        )

    assert exc_info.value.code == "NOT_FOUND"


def test_publication_guard_rejects_conflicting_versions_for_one_material(
    db: Session,
    context_seed,
) -> None:
    material = context_seed.math_material

    with pytest.raises(CourseNexusError) as exc_info:
        assert_material_snapshot_publishable(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_versions=[
                {"material_id": material.id, "version_id": material.active_parse_version_id},
                {"material_id": material.id, "version_id": "mpv_other"},
            ],
        )

    assert exc_info.value.code == "MATERIAL_SCOPE_STALE"
