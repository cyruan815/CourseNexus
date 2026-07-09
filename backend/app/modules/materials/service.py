from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.file_storage.base import FileStorage, material_type_for_filename
from app.integrations.parsers.base import Parser
from app.modules.courses.service import assert_course_owner
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.repository import (
    get_active_material_for_user,
    list_active_materials_for_course,
    replace_material_chunks,
    save_material,
)
from app.modules.materials.schemas import MaterialLinkCreate


def _new_material_id() -> str:
    return f"mat_{uuid4().hex}"


def _new_chunk_id() -> str:
    return f"chk_{uuid4().hex}"


def _material_type_for_filename(filename: str) -> str:
    return material_type_for_filename(filename)


def upload_file_material(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    filename: str,
    stream: BinaryIO,
    content_type: str | None,
    storage: FileStorage,
) -> CourseMaterial:
    assert_course_owner(db, user_id, course_id)
    material_id = _new_material_id()
    stored_file = storage.save_file(
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        filename=filename,
        stream=stream,
        content_type=content_type,
    )
    material = CourseMaterial(
        id=material_id,
        course_id=course_id,
        user_id=user_id,
        name=stored_file.filename,
        material_type=_material_type_for_filename(stored_file.filename),
        source_type="file",
        file_url=stored_file.relative_path,
        file_size=stored_file.size,
        mime_type=stored_file.mime_type,
        parse_status="uploaded",
    )
    return save_material(db, material)


def create_link_material(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: MaterialLinkCreate,
) -> CourseMaterial:
    assert_course_owner(db, user_id, course_id)
    material = CourseMaterial(
        id=_new_material_id(),
        course_id=course_id,
        user_id=user_id,
        name=payload.name,
        material_type="link",
        source_type="url",
        source_url=payload.source_url,
        parse_status="uploaded",
    )
    return save_material(db, material)


def list_course_materials(db: Session, user_id: str, course_id: str) -> list[CourseMaterial]:
    assert_course_owner(db, user_id, course_id)
    return list_active_materials_for_course(db, user_id, course_id)


def get_material_detail(db: Session, user_id: str, material_id: str) -> CourseMaterial:
    material = get_active_material_for_user(db, user_id, material_id)
    if material is None:
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)
    return material


def delete_material(db: Session, user_id: str, material_id: str) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    now = datetime.now(timezone.utc)
    material.parse_status = "deleted"
    material.deleted_at = now
    material.updated_at = now
    return save_material(db, material)


def parse_material(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    parser: Parser,
    storage_root: str | Path,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    material.parse_status = "parsing"
    material.parse_error = None
    material.updated_at = datetime.now(timezone.utc)
    save_material(db, material)

    if material.source_type != "file" or material.file_url is None:
        return _mark_parse_failed(db, material, "UNSUPPORTED_FILE_TYPE")

    try:
        parsed_document = parser.parse(Path(storage_root) / material.file_url)
    except CourseNexusError as exc:
        return _mark_parse_failed(db, material, exc.code)
    except Exception:
        return _mark_parse_failed(db, material, "PARSE_FAILED")

    chunks = [
        MaterialChunk(
            id=_new_chunk_id(),
            material_id=material.id,
            course_id=material.course_id,
            chunk_index=chunk.chunk_index,
            page=chunk.page,
            page_index=chunk.page_index,
            heading=chunk.heading,
            content_text=chunk.content_text,
        )
        for chunk in parsed_document.chunks
    ]
    material.parse_status = "parsed"
    material.parse_error = None
    material.updated_at = datetime.now(timezone.utc)
    return replace_material_chunks(db, material=material, chunks=chunks)


def _mark_parse_failed(db: Session, material: CourseMaterial, error_code: str) -> CourseMaterial:
    material.parse_status = "parse_failed"
    material.parse_error = error_code
    material.updated_at = datetime.now(timezone.utc)
    return replace_material_chunks(db, material=material, chunks=[])
