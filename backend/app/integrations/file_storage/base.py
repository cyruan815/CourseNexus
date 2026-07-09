from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


@dataclass(frozen=True)
class StoredFile:
    filename: str
    relative_path: str
    absolute_path: Path
    size: int
    mime_type: str


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
