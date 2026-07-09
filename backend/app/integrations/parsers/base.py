from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ParsedChunk:
    chunk_index: int
    content_text: str
    heading: str | None = None
    page: str | None = None
    page_index: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    chunks: list[ParsedChunk]


class Parser(Protocol):
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a local file into ordered text chunks."""
