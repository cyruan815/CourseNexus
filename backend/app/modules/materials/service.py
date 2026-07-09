from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.integrations.file_storage.base import FileStorage, material_type_for_filename
from app.integrations.parsers.base import Parser
from app.integrations.rag.base import RagChunk, RagIndex
from app.modules.courses.service import assert_course_owner
from app.modules.materials.models import CourseMaterial, MaterialChunk
from app.modules.materials.repository import (
    get_active_material_for_user,
    list_active_materials_for_course,
    replace_material_chunks,
    replace_material_chunks_in_session,
    save_material,
)
from app.modules.materials.schemas import MaterialLinkCreate


def _new_material_id() -> str:
    return f"mat_{uuid4().hex}"


def _chunk_id(material_id: str, chunk_index: int) -> str:
    return f"chk_{material_id.removeprefix('mat_')}_{chunk_index:06d}"


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


def delete_material(
    db: Session,
    user_id: str,
    material_id: str,
    *,
    rag_index: RagIndex,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    rag_index.delete_material(material.id)
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
    rag_index: RagIndex,
    storage_root: str | Path,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    material.parse_status = "parsing"
    material.parse_error = None
    material.updated_at = datetime.now(timezone.utc)
    save_material(db, material)

    if material.source_type != "file" or material.file_url is None:
        return _mark_parse_failed(db, material, "UNSUPPORTED_FILE_TYPE", rag_index=rag_index)

    try:
        parsed_document = parser.parse(Path(storage_root) / material.file_url)
    except CourseNexusError as exc:
        return _mark_parse_failed(db, material, exc.code, rag_index=rag_index)
    except Exception:
        return _mark_parse_failed(db, material, "PARSE_FAILED", rag_index=rag_index)

    chunks = [
        MaterialChunk(
            id=_chunk_id(material.id, chunk.chunk_index),
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
    replace_material_chunks_in_session(db, material=material, chunks=chunks)
    db.commit()
    db.refresh(material)

    try:
        rag_index.delete_material(material.id)
        rag_index.index_chunks(_rag_chunks_for_material(material, chunks))
    except CourseNexusError as exc:
        _try_delete_material_vectors(rag_index, material.id)
        return _mark_parse_failed(db, material, exc.code)
    except Exception:
        _try_delete_material_vectors(rag_index, material.id)
        return _mark_parse_failed(db, material, "INDEXING_FAILED")

    for chunk in chunks:
        chunk.embedding_id = chunk.id
    material.parse_status = "parsed"
    material.parse_error = None
    material.updated_at = datetime.now(timezone.utc)
    db.add_all(chunks)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def _rag_chunks_for_material(material: CourseMaterial, chunks: list[MaterialChunk]) -> list[RagChunk]:
    return [
        RagChunk(
            chunk_id=chunk.id,
            user_id=material.user_id,
            course_id=material.course_id,
            material_id=material.id,
            folder_id=material.folder_id,
            chunk_index=chunk.chunk_index,
            text=chunk.content_text,
            page=chunk.page,
            page_index=chunk.page_index,
            heading=chunk.heading,
        )
        for chunk in chunks
    ]


def _mark_parse_failed(
    db: Session,
    material: CourseMaterial,
    error_code: str,
    *,
    rag_index: RagIndex | None = None,
) -> CourseMaterial:
    if rag_index is not None:
        _try_delete_material_vectors(rag_index, material.id)
    material.parse_status = "parse_failed"
    material.parse_error = error_code
    material.updated_at = datetime.now(timezone.utc)
    return replace_material_chunks(db, material=material, chunks=[])


def _try_delete_material_vectors(rag_index: RagIndex, material_id: str) -> None:
    try:
        rag_index.delete_material(material_id)
    except Exception:
        pass
