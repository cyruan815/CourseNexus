from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.file_storage.base import FileStorage, StagedFileDeletion, material_type_for_filename
from app.integrations.parsers.base import ParseDiagnostics, Parser
from app.integrations.rag.base import RagChunk, RagIndex
from app.modules.course_qa.citations import detach_material_references
from app.modules.courses.service import assert_course_owner
from app.modules.materials.models import CourseMaterial, MaterialChunk, MaterialFolder, MaterialParseVersion
from app.modules.materials.repository import (
    delete_material_chunks_for_parse_version_in_session,
    get_building_parse_version,
    get_active_material_folder_for_user,
    get_active_material_for_user,
    get_parse_version_for_material,
    list_active_material_folders_for_course,
    list_active_materials_for_course,
    list_material_chunks_for_parse_version,
    list_material_chunks_for_material_ids,
    list_materials_for_folder,
    next_material_folder_sort_order,
    save_material,
    save_material_folder,
)
from app.modules.materials.schemas import MaterialFolderCreate, MaterialFolderUpdate, MaterialUpdate


parse_logger = get_logger("materials.parse")
index_logger = get_logger("rag.index")


def _new_material_id() -> str:
    return f"mat_{uuid4().hex}"


def _new_material_folder_id() -> str:
    return f"fld_{uuid4().hex}"


def _new_parse_version_id() -> str:
    return f"mpv_{uuid4().hex}"


def _chunk_id(parse_version_id: str, chunk_index: int) -> str:
    return f"chk_{parse_version_id.removeprefix('mpv_')}_{chunk_index:06d}"


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
    try:
        return save_material(db, material)
    except Exception:
        db.rollback()
        storage.discard_material_files(
            user_id=user_id,
            course_id=course_id,
            material_id=material_id,
        )
        raise


def list_course_materials(db: Session, user_id: str, course_id: str) -> list[CourseMaterial]:
    assert_course_owner(db, user_id, course_id)
    return list_active_materials_for_course(db, user_id, course_id)


def get_material_detail(db: Session, user_id: str, material_id: str) -> CourseMaterial:
    material = get_active_material_for_user(db, user_id, material_id)
    if material is None:
        raise CourseNexusError(code="NOT_FOUND", message="资料不存在", status_code=404)
    return material


def get_material_file_content(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    storage_root: str | Path,
) -> tuple[CourseMaterial, Path]:
    material = get_material_detail(db, user_id, material_id)
    if material.source_type != "file" or material.file_url is None:
        raise CourseNexusError(
            code="PREVIEW_UNSUPPORTED",
            message="当前资料没有可预览的原文件",
            status_code=415,
        )

    root_path = Path(storage_root).resolve()
    file_path = (root_path / material.file_url).resolve()
    try:
        file_path.relative_to(root_path)
    except ValueError as exc:
        raise CourseNexusError(
            code="PREVIEW_FILE_UNAVAILABLE",
            message="资料原文件不可用",
            status_code=404,
        ) from exc

    if not file_path.is_file():
        raise CourseNexusError(
            code="PREVIEW_FILE_UNAVAILABLE",
            message="资料原文件不可用",
            status_code=404,
        )
    return material, file_path


def rename_material(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    payload: MaterialUpdate,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    material.name = payload.name
    material.updated_at = datetime.now(timezone.utc)
    return save_material(db, material)


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
    storage: FileStorage,
) -> MaterialFolder:
    folder = get_material_folder(db, user_id, folder_id)
    materials = list_materials_for_folder(db, user_id, folder_id)
    _permanently_delete_materials(
        db,
        materials=materials,
        rag_index=rag_index,
        storage=storage,
        folder=folder,
    )
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
    if material.active_parse_version_id is not None:
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
    storage: FileStorage,
) -> CourseMaterial:
    material = get_material_detail(db, user_id, material_id)
    _permanently_delete_materials(
        db,
        materials=[material],
        rag_index=rag_index,
        storage=storage,
    )
    return material


def parse_material(
    db: Session,
    *,
    user_id: str,
    material_id: str,
    parser: Parser,
    rag_index: RagIndex,
    storage_root: str | Path,
) -> CourseMaterial:
    started_at = perf_counter()
    material = get_material_detail(db, user_id, material_id)
    if material.source_type == "url":
        raise CourseNexusError(
            code="MATERIAL_LINK_REMOVED",
            message="链接资料入口已停止支持，无法解析；请上传文件资料",
            status_code=409,
        )
    candidate = _create_parse_candidate(db, material)

    if material.source_type != "file" or material.file_url is None:
        parse_logger.warning(
            "解析失败：不支持的资料类型 | code=UNSUPPORTED_FILE_TYPE material=%s cost_ms=%.2f",
            material.id,
            (perf_counter() - started_at) * 1000,
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="UNSUPPORTED_FILE_TYPE",
            rag_index=rag_index,
        )

    try:
        parsed_document = parser.parse(Path(storage_root) / material.file_url)
    except CourseNexusError as exc:
        cause = exc.__cause__
        parse_logger.error(
            "解析失败：文件内容无法识别 | code=%s material=%s cost_ms=%.2f",
            exc.code,
            material.id,
            (perf_counter() - started_at) * 1000,
            exc_info=(type(cause), cause, cause.__traceback__) if cause is not None else None,
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code=exc.code,
            rag_index=rag_index,
        )
    except Exception as exc:
        parse_logger.error(
            "解析失败：文件内容无法识别 | code=PARSE_FAILED material=%s cost_ms=%.2f",
            material.id,
            (perf_counter() - started_at) * 1000,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="PARSE_FAILED",
            rag_index=rag_index,
        )

    chunks = [
        MaterialChunk(
            id=_chunk_id(candidate.id, chunk.chunk_index),
            material_id=material.id,
            parse_version_id=candidate.id,
            course_id=material.course_id,
            chunk_index=chunk.chunk_index,
            page=chunk.page,
            page_index=chunk.page_index,
            heading=chunk.heading,
            content_text=chunk.content_text,
        )
        for chunk in parsed_document.chunks
    ]
    if not chunks:
        parse_logger.warning(
            "候选解析版本没有可用内容 | code=PARSE_FAILED material=%s version=%s cost_ms=%.2f",
            material.id,
            candidate.id,
            (perf_counter() - started_at) * 1000,
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="PARSE_FAILED",
            rag_index=rag_index,
        )
    try:
        candidate.parse_quality = _parse_quality(parsed_document.diagnostics)
        candidate.page_count = parsed_document.diagnostics.page_count
        candidate.parse_diagnostics_json = _parse_diagnostics_json(parsed_document.diagnostics)
        candidate.updated_at = datetime.now(timezone.utc)
        db.add(candidate)
        db.add_all(chunks)
        db.commit()
    except Exception as exc:
        db.rollback()
        parse_logger.error(
            "候选解析版本保存失败 | code=PARSE_FAILED material=%s version=%s chunks=%d cost_ms=%.2f",
            material.id,
            candidate.id,
            len(chunks),
            (perf_counter() - started_at) * 1000,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="PARSE_FAILED",
            rag_index=rag_index,
        )

    try:
        rag_index.index_chunks(_rag_chunks_for_material(material, chunks))
        expected_chunk_ids = {chunk.id for chunk in chunks}
        indexed_chunk_ids = rag_index.list_parse_version_chunk_ids(candidate.id)
        if indexed_chunk_ids != expected_chunk_ids:
            raise CourseNexusError(
                code="INDEXING_FAILED",
                message="候选解析版本索引不完整",
                status_code=502,
                details={
                    "expected_count": len(expected_chunk_ids),
                    "indexed_count": len(indexed_chunk_ids),
                },
            )
    except CourseNexusError as exc:
        cause = exc.__cause__
        index_logger.error(
            "索引失败 | code=INDEXING_FAILED material=%s chunks=%d cost_ms=%.2f",
            material.id,
            len(chunks),
            (perf_counter() - started_at) * 1000,
            exc_info=(type(cause), cause, cause.__traceback__) if cause is not None else None,
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="INDEXING_FAILED",
            rag_index=rag_index,
        )
    except Exception as exc:
        index_logger.error(
            "索引失败 | code=INDEXING_FAILED material=%s chunks=%d cost_ms=%.2f",
            material.id,
            len(chunks),
            (perf_counter() - started_at) * 1000,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return _mark_parse_candidate_failed(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            error_code="INDEXING_FAILED",
            rag_index=rag_index,
        )

    try:
        material = _activate_parse_candidate(
            db,
            material_id=material.id,
            parse_version_id=candidate.id,
            chunk_ids=expected_chunk_ids,
        )
    except Exception as exc:
        db.rollback()
        current_material = db.get(CourseMaterial, material.id)
        current_candidate = db.get(MaterialParseVersion, candidate.id)
        if (
            current_material is not None
            and current_candidate is not None
            and current_material.active_parse_version_id == current_candidate.id
            and current_candidate.status == "active"
        ):
            material = current_material
        else:
            index_logger.error(
                "解析版本切换失败 | code=PARSE_VERSION_SWITCH_FAILED material=%s version=%s cost_ms=%.2f",
                material.id,
                candidate.id,
                (perf_counter() - started_at) * 1000,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            return _mark_parse_candidate_failed(
                db,
                material_id=material.id,
                parse_version_id=candidate.id,
                error_code="PARSE_VERSION_SWITCH_FAILED",
                rag_index=rag_index,
            )
    page_count = len({chunk.page_index for chunk in chunks if chunk.page_index is not None})
    parse_logger.info(
        "解析成功 | material=%s pages=%d chunks=%d cost_ms=%.2f",
        material.id,
        page_count,
        len(chunks),
        (perf_counter() - started_at) * 1000,
    )
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
            parse_version_id=chunk.parse_version_id,
        )
        for chunk in chunks
    ]


def _create_parse_candidate(db: Session, material: CourseMaterial) -> MaterialParseVersion:
    if get_building_parse_version(db, material.id) is not None:
        raise CourseNexusError(
            code="PARSE_ALREADY_IN_PROGRESS",
            message="资料正在解析，请勿重复提交",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    candidate = MaterialParseVersion(
        id=_new_parse_version_id(),
        material_id=material.id,
        course_id=material.course_id,
        user_id=material.user_id,
        status="building",
        parse_quality="unknown",
        created_at=now,
        updated_at=now,
    )
    material.parse_status = "parsing"
    material.parse_error = None
    if material.active_parse_version_id is None:
        material.parse_quality = "unknown"
        material.page_count = None
        material.parse_diagnostics_json = None
    material.updated_at = now
    db.add(candidate)
    db.add(material)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise CourseNexusError(
            code="PARSE_ALREADY_IN_PROGRESS",
            message="资料正在解析，请勿重复提交",
            status_code=409,
        ) from exc
    db.refresh(candidate)
    db.refresh(material)
    return candidate


def _activate_parse_candidate(
    db: Session,
    *,
    material_id: str,
    parse_version_id: str,
    chunk_ids: set[str],
) -> CourseMaterial:
    material = db.get(CourseMaterial, material_id)
    candidate = get_parse_version_for_material(
        db,
        material_id=material_id,
        parse_version_id=parse_version_id,
    )
    if material is None or candidate is None or candidate.status != "building":
        raise CourseNexusError(
            code="PARSE_VERSION_SWITCH_FAILED",
            message="候选解析版本状态已变化",
            status_code=409,
        )

    now = datetime.now(timezone.utc)
    if material.active_parse_version_id is not None:
        previous = get_parse_version_for_material(
            db,
            material_id=material_id,
            parse_version_id=material.active_parse_version_id,
        )
        if previous is not None:
            previous.status = "retired"
            previous.updated_at = now
            previous.finished_at = now
            db.add(previous)

    chunks = list_material_chunks_for_parse_version(db, parse_version_id)
    if {chunk.id for chunk in chunks} != chunk_ids:
        raise CourseNexusError(
            code="PARSE_VERSION_SWITCH_FAILED",
            message="候选解析版本数据不完整",
            status_code=409,
        )
    for chunk in chunks:
        chunk.embedding_id = chunk.id

    candidate.status = "active"
    candidate.parse_error = None
    candidate.activated_at = now
    candidate.finished_at = now
    candidate.updated_at = now
    material.active_parse_version_id = candidate.id
    material.parse_status = "parsed"
    material.parse_error = None
    material.parse_quality = candidate.parse_quality
    material.page_count = candidate.page_count
    material.parse_diagnostics_json = candidate.parse_diagnostics_json
    material.updated_at = now
    db.add_all(chunks)
    db.add(candidate)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def _mark_parse_candidate_failed(
    db: Session,
    *,
    material_id: str,
    parse_version_id: str,
    error_code: str,
    rag_index: RagIndex,
) -> CourseMaterial:
    db.rollback()
    _try_delete_parse_version_vectors(rag_index, parse_version_id)
    material = db.get(CourseMaterial, material_id)
    candidate = get_parse_version_for_material(
        db,
        material_id=material_id,
        parse_version_id=parse_version_id,
    )
    if material is None or candidate is None:
        raise CourseNexusError(
            code="PARSE_VERSION_SWITCH_FAILED",
            message="候选解析版本不存在",
            status_code=500,
        )

    if material.active_parse_version_id == candidate.id and candidate.status == "active":
        return material

    now = datetime.now(timezone.utc)
    delete_material_chunks_for_parse_version_in_session(db, candidate.id)
    candidate.status = "failed"
    candidate.parse_error = error_code
    candidate.updated_at = now
    candidate.finished_at = now
    if material.active_parse_version_id is None:
        material.parse_status = "parse_failed"
        material.parse_quality = "unknown"
        material.page_count = None
        material.parse_diagnostics_json = None
    else:
        material.parse_status = "parsed"
    material.parse_error = error_code
    material.updated_at = now
    db.add(candidate)
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def _try_delete_parse_version_vectors(rag_index: RagIndex, parse_version_id: str) -> None:
    try:
        rag_index.delete_parse_version(parse_version_id)
    except Exception:
        pass


def _permanently_delete_materials(
    db: Session,
    *,
    materials: list[CourseMaterial],
    rag_index: RagIndex,
    storage: FileStorage,
    folder: MaterialFolder | None = None,
) -> None:
    material_ids = [material.id for material in materials]
    chunks = list_material_chunks_for_material_ids(db, material_ids)
    versioned_materials = {
        material.id: material for material in materials if material.active_parse_version_id is not None
    }
    chunks_by_material: dict[str, list[MaterialChunk]] = {
        material_id: [] for material_id in versioned_materials
    }
    for chunk in chunks:
        if chunk.material_id in chunks_by_material:
            chunks_by_material[chunk.material_id].append(chunk)
    rag_snapshot = [
        rag_chunk
        for material_id, material in versioned_materials.items()
        for rag_chunk in _rag_chunks_for_material(material, chunks_by_material[material_id])
    ]
    staged_files = _stage_material_file_deletions(storage, materials)
    now = datetime.now(timezone.utc)

    try:
        detach_material_references(db, material_ids)
        for chunk in chunks:
            db.delete(chunk)
        db.flush()
        for material in materials:
            material.parse_status = "deleted"
            material.deleted_at = now
            material.updated_at = now
            db.delete(material)
        if folder is not None:
            folder.deleted_at = now
            folder.updated_at = now
            db.delete(folder)

        rag_index.delete_materials(material_ids)
        db.commit()
    except Exception as exc:
        db.rollback()
        _compensate_failed_permanent_deletion(
            rag_index=rag_index,
            rag_snapshot=rag_snapshot,
            staged_files=staged_files,
            operation_error=exc,
        )
        raise

    _finalize_material_file_deletions(staged_files)


def _stage_material_file_deletions(
    storage: FileStorage,
    materials: list[CourseMaterial],
) -> list[StagedFileDeletion]:
    staged_files: list[StagedFileDeletion] = []
    try:
        for material in materials:
            if material.source_type != "file":
                continue
            staged_files.append(
                storage.stage_material_deletion(
                    user_id=material.user_id,
                    course_id=material.course_id,
                    material_id=material.id,
                )
            )
    except Exception:
        for staged_file in reversed(staged_files):
            staged_file.restore()
        raise
    return staged_files


def _compensate_failed_permanent_deletion(
    *,
    rag_index: RagIndex,
    rag_snapshot: list[RagChunk],
    staged_files: list[StagedFileDeletion],
    operation_error: Exception,
) -> None:
    compensation_errors: list[Exception] = []
    try:
        _restore_rag_snapshot(rag_index, rag_snapshot, operation_error=operation_error)
    except Exception as exc:
        compensation_errors.append(exc)
    for staged_file in reversed(staged_files):
        try:
            staged_file.restore()
        except Exception as exc:
            compensation_errors.append(exc)

    if compensation_errors:
        raise CourseNexusError(
            code="DELETE_COMPENSATION_FAILED",
            message="资料删除失败且补偿未完成，请检查文件和重建资料索引",
            status_code=500,
            details={"rebuild_required": True, "file_check_required": True},
        ) from compensation_errors[0]


def _finalize_material_file_deletions(staged_files: list[StagedFileDeletion]) -> None:
    try:
        for staged_file in staged_files:
            staged_file.finalize()
    except Exception as exc:
        index_logger.error(
            "资料数据库已删除但暂存文件清理失败 | code=FILE_DELETE_FAILED",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        raise CourseNexusError(
            code="FILE_DELETE_FAILED",
            message="资料记录已删除，但文件清理失败",
            status_code=500,
            details={"cleanup_required": True},
        ) from exc


def _restore_rag_snapshot(
    rag_index: RagIndex,
    snapshot: list[RagChunk],
    *,
    operation_error: Exception,
) -> None:
    if not snapshot:
        return
    try:
        rag_index.index_chunks(snapshot)
    except Exception as compensation_error:
        index_logger.error(
            "资料目录删除索引补偿失败 | code=INDEXING_FAILED chunks=%d operation_error=%s",
            len(snapshot),
            type(operation_error).__name__,
            exc_info=(type(compensation_error), compensation_error, compensation_error.__traceback__),
        )
        raise CourseNexusError(
            code="INDEXING_FAILED",
            message="资料目录删除失败且索引补偿失败，请重建资料索引",
            status_code=502,
            details={"rebuild_required": True},
        ) from compensation_error


def _parse_diagnostics_json(diagnostics: ParseDiagnostics) -> dict[str, object]:
    return {
        "parser": diagnostics.parser,
        "profile": diagnostics.profile,
        "conversion_status": diagnostics.conversion_status,
        "page_count": diagnostics.page_count,
        "processed_pages": list(diagnostics.processed_pages),
        "pages_with_content": list(diagnostics.pages_with_content),
        "pages_with_chunks": list(diagnostics.pages_with_chunks),
        "failed_pages": list(diagnostics.failed_pages),
        "warnings": [
            {
                "code": warning.code,
                "message": warning.message,
                "page_no": warning.page_no,
                "component": warning.component,
                "severity": warning.severity,
            }
            for warning in diagnostics.warnings
        ],
    }


def _parse_quality(diagnostics: ParseDiagnostics) -> str:
    if diagnostics.parser == "unknown" or diagnostics.conversion_status == "unknown":
        return "unknown"
    return "partial" if diagnostics.is_partial else "complete"
