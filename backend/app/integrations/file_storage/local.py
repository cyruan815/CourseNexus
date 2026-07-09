from __future__ import annotations

import codecs
from pathlib import Path
from typing import BinaryIO

from app.core.errors import CourseNexusError
from app.integrations.file_storage.base import StoredFile


SUPPORTED_TEXT_MIME_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
}
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
CHUNK_SIZE_BYTES = 1024 * 1024


class LocalFileStorage:
    def __init__(self, *, root_path: str | Path, max_file_size_bytes: int) -> None:
        self.root_path = Path(root_path)
        self.max_file_size_bytes = max_file_size_bytes

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
        safe_filename = self._validate_filename(filename)
        mime_type = self._mime_type_for_filename(safe_filename)
        target_dir = self.root_path / user_id / course_id / material_id
        target_path = target_dir / safe_filename
        temp_path = target_path.with_name(f"{target_path.name}.tmp")
        total_size = 0
        decoder = codecs.getincrementaldecoder("utf-8")()

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with temp_path.open("wb") as output:
                while True:
                    chunk = stream.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break
                    total_size += len(chunk)
                    if total_size > self.max_file_size_bytes:
                        raise CourseNexusError(
                            code="FILE_TOO_LARGE",
                            message="文件超过大小限制",
                            status_code=413,
                            details={"max_upload_file_size_bytes": self.max_file_size_bytes},
                        )
                    try:
                        decoder.decode(chunk)
                    except UnicodeDecodeError as exc:
                        raise CourseNexusError(
                            code="UNSUPPORTED_FILE_TYPE",
                            message="文件类型不支持或无法按 UTF-8 解码",
                            status_code=415,
                        ) from exc
                    output.write(chunk)

                try:
                    decoder.decode(b"", final=True)
                except UnicodeDecodeError as exc:
                    raise CourseNexusError(
                        code="UNSUPPORTED_FILE_TYPE",
                        message="文件类型不支持或无法按 UTF-8 解码",
                        status_code=415,
                    ) from exc

            temp_path.replace(target_path)
        except Exception:
            self._cleanup_failed_write(temp_path, target_dir)
            raise

        relative_path = Path(user_id, course_id, material_id, safe_filename).as_posix()
        return StoredFile(
            filename=safe_filename,
            relative_path=relative_path,
            absolute_path=target_path,
            size=total_size,
            mime_type=mime_type,
        )

    def _validate_filename(self, filename: str) -> str:
        safe_filename = filename.strip()
        if not safe_filename:
            raise CourseNexusError(code="VALIDATION_ERROR", message="文件名不能为空", status_code=422)
        if any(separator in safe_filename for separator in ("/", "\\")) or ":" in safe_filename:
            raise CourseNexusError(code="VALIDATION_ERROR", message="文件名不能包含路径", status_code=422)
        if safe_filename in {".", ".."}:
            raise CourseNexusError(code="VALIDATION_ERROR", message="文件名不能包含路径", status_code=422)
        base_name = safe_filename.split(".", 1)[0].upper()
        if base_name in RESERVED_WINDOWS_NAMES:
            raise CourseNexusError(code="VALIDATION_ERROR", message="文件名不可用", status_code=422)
        return safe_filename

    def _mime_type_for_filename(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        mime_type = SUPPORTED_TEXT_MIME_TYPES.get(extension)
        if mime_type is None:
            raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)
        return mime_type

    def _cleanup_failed_write(self, temp_path: Path, target_dir: Path) -> None:
        if temp_path.exists():
            temp_path.unlink()
        current = target_dir
        while current != self.root_path and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent
