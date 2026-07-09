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
    scope_conditions = _scope_conditions(material_ids=material_ids, folder_ids=folder_ids)
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_parsed_context_chunks_for_scope(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
    folder_ids: list[str] | None = None,
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
        .order_by(MaterialChunk.material_id.asc(), MaterialChunk.chunk_index.asc())
    )
    scope_conditions = _scope_conditions(material_ids=material_ids, folder_ids=folder_ids)
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_context_chunks_by_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    chunk_ids: list[str],
    material_ids: list[str] | None = None,
    folder_ids: list[str] | None = None,
) -> list[ContextRow]:
    if not chunk_ids:
        return []

    statement = (
        select(MaterialChunk, CourseMaterial.name)
        .join(CourseMaterial, CourseMaterial.id == MaterialChunk.material_id)
        .where(
            MaterialChunk.id.in_(chunk_ids),
            CourseMaterial.user_id == user_id,
            CourseMaterial.course_id == course_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status == "parsed",
        )
    )
    scope_conditions = _scope_conditions(material_ids=material_ids, folder_ids=folder_ids)
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def has_parsed_context_chunks(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
    folder_ids: list[str] | None = None,
) -> bool:
    statement = (
        select(MaterialChunk.id)
        .join(CourseMaterial, CourseMaterial.id == MaterialChunk.material_id)
        .where(
            CourseMaterial.user_id == user_id,
            CourseMaterial.course_id == course_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status == "parsed",
        )
        .limit(1)
    )
    scope_conditions = _scope_conditions(material_ids=material_ids, folder_ids=folder_ids)
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return db.execute(statement).scalar_one_or_none() is not None


def list_eligible_material_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
    folder_ids: list[str] | None = None,
) -> list[str]:
    statement = (
        select(CourseMaterial.id)
        .where(
            CourseMaterial.user_id == user_id,
            CourseMaterial.course_id == course_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status == "parsed",
        )
        .order_by(CourseMaterial.id.asc())
    )
    scope_conditions = _scope_conditions(material_ids=material_ids, folder_ids=folder_ids)
    if scope_conditions:
        statement = statement.where(or_(*scope_conditions))

    return list(db.execute(statement).scalars())


def _scope_conditions(
    *,
    material_ids: list[str] | None,
    folder_ids: list[str] | None,
):
    conditions = []
    if material_ids:
        conditions.append(CourseMaterial.id.in_(material_ids))
    if folder_ids:
        conditions.append(CourseMaterial.folder_id.in_(folder_ids))
    return conditions
