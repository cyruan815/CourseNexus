from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.materials.models import CourseMaterial, MaterialChunk


ContextRow = tuple[MaterialChunk, str]


def list_parsed_context_chunks(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
    folder_ids: list[str] | None = None,
    limit: int = 20,
) -> list[ContextRow]:
    statement = (
        select(MaterialChunk, CourseMaterial.name)
        .join(CourseMaterial, CourseMaterial.id == MaterialChunk.material_id)
        .where(
            CourseMaterial.user_id == user_id,
            CourseMaterial.course_id == course_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status == "parsed",
        )
        .order_by(CourseMaterial.created_at.asc(), MaterialChunk.chunk_index.asc())
        .limit(limit)
    )
    scope_conditions = []
    if material_ids:
        scope_conditions.append(CourseMaterial.id.in_(material_ids))
    if folder_ids:
        scope_conditions.append(CourseMaterial.folder_id.in_(folder_ids))
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def count_eligible_materials(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str],
) -> int:
    return len(
        list(
            db.execute(
                select(CourseMaterial.id).where(
                    CourseMaterial.id.in_(material_ids),
                    CourseMaterial.user_id == user_id,
                    CourseMaterial.course_id == course_id,
                    CourseMaterial.deleted_at.is_(None),
                    CourseMaterial.parse_status == "parsed",
                )
            ).scalars()
        )
    )
