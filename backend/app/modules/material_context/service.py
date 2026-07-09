from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.courses.service import assert_course_owner
from app.modules.material_context.repository import count_eligible_materials, list_parsed_context_chunks
from app.modules.material_context.schemas import ContextChunk, MaterialContextResult, MaterialScope


def resolve_context(
    db: Session,
    user_id: str,
    course_id: str,
    material_scope: MaterialScope | None = None,
    limit: int = 20,
) -> MaterialContextResult:
    assert_course_owner(db, user_id, course_id)
    scope = material_scope or MaterialScope()

    material_ids: list[str] | None = None
    folder_ids: list[str] | None = None

    if scope.include_all_parsed_materials:
        material_ids = None
        folder_ids = None
    else:
        material_ids = _unique(scope.material_ids)
        folder_ids = _unique(scope.folder_ids)
        if not material_ids and not folder_ids:
            return MaterialContextResult(chunks=[], no_parsed_material=True)
        if material_ids:
            _assert_material_ids_are_eligible(db, user_id, course_id, material_ids)

    rows = list_parsed_context_chunks(
        db,
        user_id=user_id,
        course_id=course_id,
        material_ids=material_ids,
        folder_ids=folder_ids,
        limit=limit,
    )
    chunks = [
        ContextChunk(
            material_id=chunk.material_id,
            chunk_id=chunk.id,
            material_name=material_name,
            page=chunk.page,
            page_index=chunk.page_index,
            heading=chunk.heading,
            content_text=chunk.content_text,
        )
        for chunk, material_name in rows
    ]
    return MaterialContextResult(chunks=chunks, no_parsed_material=len(chunks) == 0)


def _assert_material_ids_are_eligible(
    db: Session,
    user_id: str,
    course_id: str,
    material_ids: list[str],
) -> None:
    if count_eligible_materials(db, user_id=user_id, course_id=course_id, material_ids=material_ids) != len(material_ids):
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
