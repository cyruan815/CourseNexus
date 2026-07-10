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
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder
from app.modules.materials.repository import (
    get_active_material_folder_for_user,
    get_active_material_for_user,
    list_active_material_folders_for_course,
    list_active_materials_for_course,
    list_materials_for_folder,
    next_material_folder_sort_order,
    replace_material_chunks,
    replace_material_chunks_in_session,
    save_material,
    save_material_folder,
)
from app.modules.materials.schemas import MaterialFolderCreate, MaterialFolderUpdate, MaterialLinkCreate


def _new_material_id() -> str:
    return f"mat_{uuid4().hex}"


def _new_material_folder_id() -> str:
    return f"fld_{uuid4().hex}"


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
    folder_id: str | None = None,
) -> CourseMaterial:
    assert_course_owner(db, user_id, course_id)
    _assert_folder_in_course(db, user_id=user_id, course_id=course_id, folder_id=folder_id)
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
        folder_id=folder_id,
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
    _assert_folder_in_course(db, user_id=user_id, course_id=course_id, folder_id=payload.folder_id)
    material = CourseMaterial(
        id=_new_material_id(),
        course_id=course_id,
        user_id=user_id,
        folder_id=payload.folder_id,
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


def create_material_folder(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    payload: MaterialFolderCreate,
) -> MaterialFolder:
    assert_course_owner(db, user_id, course_id)
    folder = MaterialFolder(
        id=_new_material_folder_id(),
        user_id=user_id,
        course_id=course_id,
        name=payload.name,
        sort_order=payload.sort_order or next_material_folder_sort_order(db, user_id, course_id),
    )
    return save_material_folder(db, folder)


def list_material_folders(db: Session, user_id: str, course_id: str) -> list[MaterialFolder]:
    assert_course_owner(db, user_id, course_id)
    return list_active_material_folders_for_course(db, user_id, course_id)


def get_material_folder(db: Session, user_id: str, folder_id: str) -> MaterialFolder:
    folder = get_active_material_folder_for_user(db, user_id, folder_id)
    if folder is None:
        raise CourseNexusError(code="NOT_FOUND", message="资料目录不存在", status_code=404)
    return folder


def update_material_folder(
    db: Session,
    *,
    user_id: str,
    folder_id: str,
    payload: MaterialFolderUpdate,
) -> MaterialFolder:
    folder = get_material_folder(db, user_id, folder_id)
    if payload.name is not None:
        folder.name = payload.name
    if payload.sort_order is not None:
        folder.sort_order = payload.sort_order
    folder.updated_at = datetime.now(timezone.utc)
    return save_material_folder(db, folder)


def delete_material_folder(
    db: Session,
    *,
    user_id: str,
    folder_id: str,
    rag_index: RagIndex,
) -> MaterialFolder:
    folder = get_material_folder(db, user_id, folder_id)
    materials = list_materials_for_folder(db, user_id, folder_id)
    for material in materials:
        if material.parse_status == "parsed" and material.deleted_at is None:
            rag_index.update_material_folder(material.id, None)

    now = datetime.now(timezone.utc)
    for material in materials:
        material.folder_id = None
        material.updated_at = now
        db.add(material)
    folder.deleted_at = now
    folder.updated_at = now
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def move_material_to_folder(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    folder_id: str | None,
    rag_index: RagIndex,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    _assert_folder_in_course(db, user_id=user_id, course_id=material.course_id, folder_id=folder_id)
    if material.folder_id == folder_id:
        return material
    if material.parse_status == "parsed":
        rag_index.update_material_folder(material.id, folder_id)
    material.folder_id = folder_id
    material.updated_at = datetime.now(timezone.utc)
    return save_material(db, material)


def _assert_folder_in_course(
    db: Session,
    *,
    user_id: str,
    course_id: str,
    folder_id: str | None,
) -> None:
    if folder_id is None:
        return
    folder = get_material_folder(db, user_id, folder_id)
    if folder.course_id != course_id:
        raise CourseNexusError(code="NOT_FOUND", message="资料目录不存在", status_code=404)


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
    except CourseNexusError:
        _try_delete_material_vectors(rag_index, material.id)
        return _mark_parse_failed(db, material, "INDEXING_FAILED")
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
