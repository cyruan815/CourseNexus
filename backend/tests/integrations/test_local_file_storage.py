from __future__ import annotations

from io import BytesIO
import logging
from pathlib import Path
import zipfile

import pytest

from app.core.config import Settings
from app.core.errors import CourseNexusError
from app.integrations.file_storage.local import LocalFileStorage


def capture_course_logs(caplog) -> logging.Logger:
    logger = logging.getLogger("course_nexus")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    return logger


def office_stream(member_name: str) -> BytesIO:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(member_name, "<xml />")
    stream.seek(0)
    return stream


def test_upload_file_size_limit_has_default_setting() -> None:
    assert Settings().max_upload_file_size_bytes == 52_428_800


def test_local_file_storage_saves_text_file_under_scoped_directory(tmp_path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    stored_file = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename="notes.md",
        stream=BytesIO(b"# Chapter 1\n"),
        content_type="application/octet-stream",
    )

    assert stored_file.size == 12
    assert stored_file.mime_type == "text/markdown"
    assert stored_file.filename == "notes.md"
    assert stored_file.relative_path == "usr_1/crs_1/mat_1/source.md"
    assert (tmp_path / stored_file.relative_path).read_text(encoding="utf-8") == "# Chapter 1\n"


def test_staged_material_deletion_can_be_restored_or_finalized(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    stored = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename="notes.txt",
        stream=BytesIO(b"notes"),
    )
    source_path = tmp_path / stored.relative_path

    staged = storage.stage_material_deletion(user_id="usr_1", course_id="crs_1", material_id="mat_1")
    assert not source_path.exists()
    staged.restore()
    assert source_path.read_bytes() == b"notes"

    staged = storage.stage_material_deletion(user_id="usr_1", course_id="crs_1", material_id="mat_1")
    staged.finalize()

    assert not source_path.exists()
    assert not (tmp_path / "usr_1" / "crs_1" / "mat_1").exists()
    assert not (tmp_path / ".trash").exists()


def test_save_file_logs_success_without_file_content(tmp_path: Path, caplog) -> None:
    logger = capture_course_logs(caplog)
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)
    secret_content = b"private course notes"
    try:
        stored = storage.save_file(
            user_id="user_1",
            course_id="course_1",
            material_id="mat_1",
            filename="notes.txt",
            stream=BytesIO(secret_content),
        )
    finally:
        logger.removeHandler(caplog.handler)

    record = next(record for record in caplog.records if record.name.endswith("materials.upload"))
    assert "上传成功" in record.getMessage()
    assert "material=mat_1" in record.getMessage()
    assert f"size={stored.size}" in record.getMessage()
    assert "private course notes" not in record.getMessage()


def test_local_file_storage_preserves_display_name_but_uses_ascii_internal_path(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    saved = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename="Chap7 物理层.pdf",
        stream=BytesIO(b"%PDF-1.7\n%%EOF"),
        content_type="application/octet-stream",
    )

    assert saved.filename == "Chap7 物理层.pdf"
    assert saved.relative_path == "usr_1/crs_1/mat_1/source.pdf"
    assert (tmp_path / saved.relative_path).read_bytes() == b"%PDF-1.7\n%%EOF"
    assert "物理层" not in str(tmp_path / saved.relative_path)


def test_storage_accepts_pdf_signature(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    saved = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename="slides.pdf",
        stream=BytesIO(b"%PDF-1.7\n%%EOF"),
        content_type="application/octet-stream",
    )

    assert saved.mime_type == "application/pdf"


@pytest.mark.parametrize(
    ("filename", "stream", "mime_type"),
    [
        (
            "notes.docx",
            office_stream("word/document.xml"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        (
            "slides.pptx",
            office_stream("ppt/presentation.xml"),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ),
        ("image.png", BytesIO(b"\x89PNG\r\n\x1a\nrest"), "image/png"),
        ("photo.jpg", BytesIO(b"\xff\xd8\xff\xe0rest"), "image/jpeg"),
        ("photo.jpeg", BytesIO(b"\xff\xd8\xff\xe0rest"), "image/jpeg"),
    ],
)
def test_storage_accepts_supported_binary_formats(
    tmp_path: Path,
    filename: str,
    stream: BytesIO,
    mime_type: str,
) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    saved = storage.save_file(
        user_id="usr_1",
        course_id="crs_1",
        material_id="mat_1",
        filename=filename,
        stream=stream,
    )

    assert saved.mime_type == mime_type
    assert (tmp_path / saved.relative_path).exists()


def test_storage_rejects_fake_docx(tmp_path: Path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    with pytest.raises(CourseNexusError) as exc_info:
        storage.save_file(
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            filename="notes.docx",
            stream=BytesIO(b"not-a-zip"),
        )

    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.parametrize("filename", ["../notes.md", "folder/notes.md", "C:\\notes.md", "CON.md", ""])
def test_local_file_storage_rejects_unsafe_filename(tmp_path, filename: str) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    with pytest.raises(CourseNexusError) as exc_info:
        storage.save_file(
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            filename=filename,
            stream=BytesIO(b"hello"),
            content_type="text/plain",
        )

    assert exc_info.value.code == "VALIDATION_ERROR"


def test_local_file_storage_rejects_large_file_and_cleans_temp_file(tmp_path, caplog) -> None:
    logger = capture_course_logs(caplog)
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4)

    try:
        with pytest.raises(CourseNexusError) as exc_info:
            storage.save_file(
                user_id="usr_1",
                course_id="crs_1",
                material_id="mat_1",
                filename="notes.txt",
                stream=BytesIO(b"12345"),
                content_type="text/plain",
            )
    finally:
        logger.removeHandler(caplog.handler)

    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert list(tmp_path.rglob("*")) == []
    record = next(record for record in caplog.records if record.name.endswith("materials.upload"))
    assert "上传被拒绝：文件过大" in record.getMessage()
    assert "code=FILE_TOO_LARGE" in record.getMessage()


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("notes.txt", b"\xff\xfe\x00"),
        ("slides.pdf", b"not-a-pdf"),
        ("image.png", b"not-a-png"),
        ("photo.jpg", b"not-a-jpeg"),
    ],
)
def test_local_file_storage_rejects_unsupported_or_non_utf8_files(tmp_path, filename: str, content: bytes) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=1024)

    with pytest.raises(CourseNexusError) as exc_info:
        storage.save_file(
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            filename=filename,
            stream=BytesIO(content),
            content_type="application/octet-stream",
        )

    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"
