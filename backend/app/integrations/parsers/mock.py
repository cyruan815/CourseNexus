from __future__ import annotations

from pathlib import Path

from app.integrations.parsers.base import ParsedChunk, ParsedDocument


class MockParser:
    def __init__(self, chunks: list[ParsedChunk] | None = None) -> None:
        self.chunks = chunks or [ParsedChunk(chunk_index=0, content_text="mock chunk")]

    def parse(self, file_path: Path) -> ParsedDocument:
        return ParsedDocument(chunks=self.chunks)
