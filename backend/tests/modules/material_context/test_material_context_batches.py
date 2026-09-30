from __future__ import annotations

from io import BytesIO

from sqlalchemy.orm import Session

from app.integrations.file_storage.local import LocalFileStorage
from app.integrations.parsers.plain_text import PlainTextParser
from app.integrations.rag.fake import FakeRagIndex
from app.modules.material_context.schemas import MaterialScope
from app.modules.material_context.service import (
    iter_material_context_batches,
    summarize_material_quality_for_scope,
)
from app.modules.materials.models import MaterialParseVersion
from app.modules.materials.service import parse_material, upload_file_material


def test_batches_cover_every_selected_material(db: Session, context_seed) -> None:
    selected_ids = {context_seed.math_material.id, context_seed.history_material.id}

    batches = list(
        iter_material_context_batches(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=list(selected_ids),
            ),
            max_tokens=20,
        )
    )

    flattened = [chunk for batch in batches for chunk in batch.chunks]
    assert {chunk.material_id for chunk in flattened} == selected_ids
    assert {material_id for batch in batches for material_id in batch.material_ids} == selected_ids
    assert all(batch.estimated_tokens > 0 for batch in batches)


def test_batches_are_ordered_by_material_id_and_chunk_index(db: Session, context_seed) -> None:
    batches = list(
        iter_material_context_batches(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[context_seed.history_material.id, context_seed.math_material.id],
            ),
            max_tokens=100,
        )
    )

    flattened = [chunk for batch in batches for chunk in batch.chunks]
    assert [(chunk.material_id, chunk.chunk_index) for chunk in flattened] == sorted(
        (chunk.material_id, chunk.chunk_index) for chunk in flattened
    )


def test_batches_never_split_oversized_chunk(db: Session, tmp_path, context_seed) -> None:
    rag_index = FakeRagIndex()
    material = upload_file_material(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        filename="large.txt",
        stream=BytesIO(("x" * 80).encode("utf-8")),
        content_type="text/plain",
        storage=LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4096),
    )
    parse_material(
        db,
        user_id=context_seed.user.id,
        material_id=material.id,
        parser=PlainTextParser(),
        rag_index=rag_index,
        storage_root=tmp_path,
    )

    batches = list(
        iter_material_context_batches(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(include_all_parsed_materials=False, material_ids=[material.id]),
            max_tokens=5,
        )
    )

    assert len(batches) == 1
    assert [chunk.chunk_id for chunk in batches[0].chunks]
    assert batches[0].estimated_tokens == 20


def test_batches_ignore_failed_material_without_active_version(db: Session, context_seed) -> None:
    batches = list(
        iter_material_context_batches(
            db,
            user_id=context_seed.user.id,
            course_id=context_seed.course.id,
            material_scope=MaterialScope(
                include_all_parsed_materials=False,
                material_ids=[context_seed.empty_material.id],
            ),
            max_tokens=20,
        )
    )

    assert batches == []


def test_material_quality_summary_maps_partial_parse_diagnostics_for_scope(db: Session, context_seed) -> None:
    active_version = db.get(MaterialParseVersion, context_seed.math_material.active_parse_version_id)
    assert active_version is not None
    active_version.parse_quality = "partial"
    active_version.page_count = 4
    active_version.parse_diagnostics_json = {
        "parser": "docling",
        "profile": "pdf_text_first",
        "conversion_status": "partial_success",
        "page_count": 4,
        "processed_pages": [1, 2, 4],
        "pages_with_content": [1, 2, 4],
        "pages_with_chunks": [1, 2],
        "failed_pages": [3],
        "warnings": [
            {
                "code": "OCR_MEMORY_ERROR",
                "message": "OCR memory limit hit",
                "page_no": 3,
                "component": "ocr",
                "severity": "warning",
            },
            {
                "code": "OCR_FALLBACK_USED",
                "message": "OCR fallback used",
                "severity": "info",
            },
        ],
    }
    db.add(active_version)
    db.commit()

    summary = summarize_material_quality_for_scope(
        db,
        user_id=context_seed.user.id,
        course_id=context_seed.course.id,
        material_scope=MaterialScope(
            include_all_parsed_materials=False,
            material_ids=[context_seed.math_material.id],
        ),
    )

    warning_codes = [warning.code for warning in summary.warnings]
    assert warning_codes == ["MATERIAL_PARSE_PARTIAL", "MATERIAL_PARSE_DIAGNOSTIC_WARNING"]
    partial_warning = summary.warnings[0]
    assert partial_warning.material_id == context_seed.math_material.id
    assert partial_warning.material_name == context_seed.math_material.name
    assert partial_warning.parse_quality == "partial"
    assert partial_warning.details["failed_pages"] == [3]
    diagnostic_warning = summary.warnings[1]
    assert diagnostic_warning.page_no == 3
    assert diagnostic_warning.component == "ocr"
    assert diagnostic_warning.details["diagnostic_code"] == "OCR_MEMORY_ERROR"
