from __future__ import annotations

from io import BytesIO

import pytest

from app.core.config import Settings
from app.core.errors import CourseNexusError
from app.integrations.file_storage.local import LocalFileStorage


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
    assert stored_file.relative_path == "usr_1/crs_1/mat_1/notes.md"
    assert (tmp_path / stored_file.relative_path).read_text(encoding="utf-8") == "# Chapter 1\n"


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


def test_local_file_storage_rejects_large_file_and_cleans_temp_file(tmp_path) -> None:
    storage = LocalFileStorage(root_path=tmp_path, max_file_size_bytes=4)

    with pytest.raises(CourseNexusError) as exc_info:
        storage.save_file(
            user_id="usr_1",
            course_id="crs_1",
            material_id="mat_1",
            filename="notes.txt",
            stream=BytesIO(b"12345"),
            content_type="text/plain",
        )

    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("notes.pdf", b"%PDF-1.7"),
        ("notes.txt", b"\xff\xfe\x00"),
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
