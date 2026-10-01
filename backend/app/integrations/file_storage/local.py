from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from time import perf_counter
from typing import BinaryIO
from uuid import uuid4
import zipfile

from app.core.errors import CourseNexusError
from app.core.logging import get_logger
from app.integrations.file_storage.base import StoredFile, mime_type_for_filename


OFFICE_REQUIRED_MEMBERS = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
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
logger = get_logger("materials.upload")


@dataclass
class _LocalStagedFileDeletion:
    original_path: Path | None
    staged_path: Path | None
    storage_root: Path
    trash_root: Path

    def finalize(self) -> None:
        if self.staged_path is not None and self.staged_path.exists():
            shutil.rmtree(self.staged_path)
        self._cleanup_original_parents()
        self._cleanup_trash_root()

    def restore(self) -> None:
        if self.original_path is not None and self.staged_path is not None and self.staged_path.exists():
            self.original_path.parent.mkdir(parents=True, exist_ok=True)
            self.staged_path.replace(self.original_path)
        self._cleanup_trash_root()

    def _cleanup_trash_root(self) -> None:
        if self.trash_root.exists():
            try:
                self.trash_root.rmdir()
            except OSError:
                pass

    def _cleanup_original_parents(self) -> None:
        if self.original_path is None:
            return
        current = self.original_path.parent
        while current != self.storage_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


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
        started_at = perf_counter()
        display_filename = filename.replace("\\", "/").rsplit("/", 1)[-1] or "-"
        try:
            safe_filename = self._validate_filename(filename)
            mime_type = self._mime_type_for_filename(safe_filename)
            extension = Path(safe_filename).suffix.lower()
            internal_filename = f"source{extension}"
            target_dir = self.root_path / user_id / course_id / material_id
            target_path = target_dir / internal_filename
            temp_path = target_path.with_name(f"{target_path.name}.tmp")
            total_size = 0

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
                        output.write(chunk)

                self._validate_file_content(temp_path, extension)
                temp_path.replace(target_path)
            except Exception:
                self._cleanup_failed_write(temp_path, target_dir)
                raise
        except CourseNexusError as exc:
            conclusion = {
                "FILE_TOO_LARGE": "文件过大",
                "VALIDATION_ERROR": "文件名不合法",
                "UNSUPPORTED_FILE_TYPE": "不支持的文件类型",
            }.get(exc.code, "文件校验失败")
            logger.warning(
                "上传被拒绝：%s | code=%s material=%s course=%s file=%s cost_ms=%.2f",
                conclusion,
                exc.code,
                material_id,
                course_id,
                display_filename,
                (perf_counter() - started_at) * 1000,
            )
            raise
        except Exception:
            logger.exception(
                "上传失败：文件保存异常 | material=%s course=%s file=%s cost_ms=%.2f",
                material_id,
                course_id,
                display_filename,
                (perf_counter() - started_at) * 1000,
            )
            raise

        relative_path = Path(user_id, course_id, material_id, internal_filename).as_posix()
        stored_file = StoredFile(
            filename=safe_filename,
            relative_path=relative_path,
            absolute_path=target_path,
            size=total_size,
            mime_type=mime_type,
        )
        logger.info(
            "上传成功 | material=%s course=%s file=%s size=%d cost_ms=%.2f",
            material_id,
            course_id,
            safe_filename,
            total_size,
            (perf_counter() - started_at) * 1000,
        )
        return stored_file

    def stage_material_deletion(
        self,
        *,
        user_id: str,
        course_id: str,
        material_id: str,
    ) -> _LocalStagedFileDeletion:
        target_dir = self._material_directory(user_id=user_id, course_id=course_id, material_id=material_id)
        trash_root = self.root_path.resolve() / ".trash"
        if not target_dir.exists():
            return _LocalStagedFileDeletion(
                original_path=None,
                staged_path=None,
                storage_root=self.root_path.resolve(),
                trash_root=trash_root,
            )

        trash_root.mkdir(parents=True, exist_ok=True)
        staged_path = trash_root / uuid4().hex
        try:
            target_dir.replace(staged_path)
        except Exception as exc:
            raise CourseNexusError(code="FILE_DELETE_FAILED", message="资料文件删除失败", status_code=500) from exc
        return _LocalStagedFileDeletion(
            original_path=target_dir,
            staged_path=staged_path,
            storage_root=self.root_path.resolve(),
            trash_root=trash_root,
        )

    def discard_material_files(
        self,
        *,
        user_id: str,
        course_id: str,
        material_id: str,
    ) -> None:
        staged = self.stage_material_deletion(
            user_id=user_id,
            course_id=course_id,
            material_id=material_id,
        )
        staged.finalize()

    def _material_directory(self, *, user_id: str, course_id: str, material_id: str) -> Path:
        parts = (user_id, course_id, material_id)
        if any(not part or Path(part).name != part for part in parts):
            raise CourseNexusError(code="FILE_DELETE_FAILED", message="资料文件路径不合法", status_code=500)
        root = self.root_path.resolve()
        target = (root / user_id / course_id / material_id).resolve()
        if not target.is_relative_to(root):
            raise CourseNexusError(code="FILE_DELETE_FAILED", message="资料文件路径不合法", status_code=500)
        return target

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
        return mime_type_for_filename(filename)

    def _validate_file_content(self, path: Path, extension: str) -> None:
        try:
            if extension in {".md", ".txt"}:
                path.read_text(encoding="utf-8")
                return
            if extension == ".pdf":
                self._require_prefix(path, b"%PDF-")
                return
            if extension == ".png":
                self._require_prefix(path, b"\x89PNG\r\n\x1a\n")
                return
            if extension in {".jpg", ".jpeg"}:
                self._require_prefix(path, b"\xff\xd8\xff")
                return
            if extension in OFFICE_REQUIRED_MEMBERS:
                self._validate_office_zip(path, OFFICE_REQUIRED_MEMBERS[extension])
                return
        except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise CourseNexusError(
                code="UNSUPPORTED_FILE_TYPE",
                message="文件类型不支持或内容无法识别",
                status_code=415,
            ) from exc
        raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)

    def _require_prefix(self, path: Path, expected_prefix: bytes) -> None:
        with path.open("rb") as file:
            actual_prefix = file.read(len(expected_prefix))
        if actual_prefix != expected_prefix:
            raise CourseNexusError(
                code="UNSUPPORTED_FILE_TYPE",
                message="文件类型不支持或内容无法识别",
                status_code=415,
            )

    def _validate_office_zip(self, path: Path, required_member: str) -> None:
        with zipfile.ZipFile(path) as archive:
            if required_member not in set(archive.namelist()):
                raise CourseNexusError(
                    code="UNSUPPORTED_FILE_TYPE",
                    message="文件类型不支持或内容无法识别",
                    status_code=415,
                )

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
