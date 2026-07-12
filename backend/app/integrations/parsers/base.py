from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol


@dataclass(frozen=True)
class ParsedChunk:
    chunk_index: int
    content_text: str
    heading: str | None = None
    page: str | None = None
    page_index: int | None = None


@dataclass(frozen=True)
class ParseWarning:
    code: str
    message: str
    page_no: int | None = None
    component: str | None = None
    severity: Literal["info", "warning"] = "warning"


@dataclass(frozen=True)
class ParseDiagnostics:
    parser: str = "unknown"
    profile: str = "unknown"
    conversion_status: str = "unknown"
    page_count: int | None = None
    processed_pages: tuple[int, ...] = ()
    pages_with_content: tuple[int, ...] = ()
    pages_with_chunks: tuple[int, ...] = ()
    failed_pages: tuple[int, ...] = ()
    warnings: tuple[ParseWarning, ...] = ()

    @property
    def is_partial(self) -> bool:
        return (
            self.conversion_status in {"partial_success", "failure"}
            or bool(self.failed_pages)
            or any(warning.severity == "warning" for warning in self.warnings)
        )


@dataclass(frozen=True)
class ParsedDocument:
    chunks: list[ParsedChunk]
    diagnostics: ParseDiagnostics = field(default_factory=ParseDiagnostics)


class Parser(Protocol):
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a local file into ordered text chunks."""
