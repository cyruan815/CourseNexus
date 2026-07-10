from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.materials.models import CourseMaterial, MaterialChunk


ContextRow = tuple[MaterialChunk, str]


def list_parsed_context_chunks(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
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
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_parsed_context_chunks_for_scope(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
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
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def list_context_chunks_by_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    chunk_ids: list[str],
    material_ids: list[str] | None = None,
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
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return [(row[0], row[1]) for row in db.execute(statement).all()]


def has_parsed_context_chunks(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
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
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return db.execute(statement).scalar_one_or_none() is not None


def list_eligible_material_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
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
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return list(db.execute(statement).scalars())


def list_active_scope_material_ids(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    material_ids: list[str] | None = None,
) -> list[str]:
    statement = (
        select(CourseMaterial.id)
        .where(
            CourseMaterial.user_id == user_id,
            CourseMaterial.course_id == course_id,
            CourseMaterial.deleted_at.is_(None),
            CourseMaterial.parse_status != "deleted",
        )
        .order_by(CourseMaterial.id.asc())
    )
    if material_ids:
        statement = statement.where(CourseMaterial.id.in_(material_ids))

    return list(db.execute(statement).scalars())
