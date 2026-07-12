from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder


def save_material_folder(db: Session, folder: MaterialFolder) -> MaterialFolder:
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def get_active_material_folder_for_user(db: Session, user_id: str, folder_id: str) -> MaterialFolder | None:
    return db.execute(
        select(MaterialFolder).where(
            MaterialFolder.id == folder_id,
            MaterialFolder.user_id == user_id,
            MaterialFolder.deleted_at.is_(None),
        )
    ).scalar_one_or_none()


def list_active_material_folders_for_course(
    db: Session,
    user_id: str,
    course_id: str,
) -> list[MaterialFolder]:
    return list(
        db.execute(
            select(MaterialFolder)
            .where(
                MaterialFolder.user_id == user_id,
                MaterialFolder.course_id == course_id,
                MaterialFolder.deleted_at.is_(None),
            )
            .order_by(
                func.coalesce(MaterialFolder.sort_order, 2_147_483_647),
                MaterialFolder.created_at,
                MaterialFolder.id,
            )
        ).scalars()
    )


def next_material_folder_sort_order(db: Session, user_id: str, course_id: str) -> int:
    current_max = db.execute(
        select(func.max(MaterialFolder.sort_order)).where(
            MaterialFolder.user_id == user_id,
            MaterialFolder.course_id == course_id,
            MaterialFolder.deleted_at.is_(None),
        )
    ).scalar_one()
    return (current_max or 0) + 1


def list_materials_for_folder(db: Session, user_id: str, folder_id: str) -> list[CourseMaterial]:
    return list(
        db.execute(
            select(CourseMaterial).where(
                CourseMaterial.user_id == user_id,
                CourseMaterial.folder_id == folder_id,
            )
        ).scalars()
    )


def list_material_chunks_for_material_ids(db: Session, material_ids: list[str]) -> list[MaterialChunk]:
    if not material_ids:
        return []
    return list(
        db.execute(
            select(MaterialChunk)
            .where(MaterialChunk.material_id.in_(material_ids))
            .order_by(MaterialChunk.material_id, MaterialChunk.chunk_index, MaterialChunk.id)
        ).scalars()
    )


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


def replace_material_chunks(
    db: Session,
    *,
    material: CourseMaterial,
    chunks: list[MaterialChunk],
) -> CourseMaterial:
    replace_material_chunks_in_session(db, material=material, chunks=chunks)
    db.commit()
    db.refresh(material)
    return material


def replace_material_chunks_in_session(
    db: Session,
    *,
    material: CourseMaterial,
    chunks: list[MaterialChunk],
) -> None:
    db.execute(delete(MaterialChunk).where(MaterialChunk.material_id == material.id))
    db.add_all(chunks)
    db.add(material)
