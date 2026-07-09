from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.materials.models import CourseMaterial


def save_material(db: Session, material: CourseMaterial) -> CourseMaterial:
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def list_active_materials_for_course(db: Session, user_id: str, course_id: str) -> list[CourseMaterial]:
    return list(
        db.execute(
            select(CourseMaterial)
            .where(
                CourseMaterial.user_id == user_id,
                CourseMaterial.course_id == course_id,
                CourseMaterial.deleted_at.is_(None),
                CourseMaterial.parse_status != "deleted",
            )
            .order_by(CourseMaterial.created_at.desc())
        ).scalars()
    )


def get_active_material_for_user(db: Session, user_id: str, material_id: str) -> CourseMaterial | None:
    return db.execute(
        select(CourseMaterial).where(
            CourseMaterial.id == material_id,
            CourseMaterial.user_id == user_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status != "deleted",
        )
    ).scalar_one_or_none()
