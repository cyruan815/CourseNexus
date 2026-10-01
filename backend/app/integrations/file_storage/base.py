from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from app.core.errors import CourseNexusError


SUPPORTED_FILE_TYPES = {
    ".md": ("text/markdown", "markdown"),
    ".txt": ("text/plain", "text"),
    ".pdf": ("application/pdf", "pdf"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "word"),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "ppt"),
    ".png": ("image/png", "image"),
    ".jpg": ("image/jpeg", "image"),
    ".jpeg": ("image/jpeg", "image"),
}


def _file_type_for_filename(filename: str) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()
    file_type = SUPPORTED_FILE_TYPES.get(extension)
    if file_type is None:
        raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)
    return file_type


def mime_type_for_filename(filename: str) -> str:
    return _file_type_for_filename(filename)[0]


def material_type_for_filename(filename: str) -> str:
    return _file_type_for_filename(filename)[1]


@dataclass(frozen=True)
class StoredFile:
    filename: str
    relative_path: str
    absolute_path: Path
    size: int
    mime_type: str


class StagedFileDeletion(Protocol):
    def finalize(self) -> None:
        """Permanently remove the staged material files."""

    def restore(self) -> None:
        """Restore staged material files to their original path."""


class FileStorage(Protocol):
    def save_file(
        self,
        *,
        user_id: str,
        course_id: str,
        material_id: str,
        filename: str,
        stream: BinaryIO,
        content_type: str | None = None,
    ) -> StoredFile:
        """Save an uploaded file and return storage metadata."""

    def stage_material_deletion(
        self,
        *,
        user_id: str,
        course_id: str,
        material_id: str,
    ) -> StagedFileDeletion:
        """Move one material's files out of active storage for commit or rollback."""

    def discard_material_files(
        self,
        *,
        user_id: str,
        course_id: str,
        material_id: str,
    ) -> None:
        """Idempotently remove one material directory after a failed upload."""
