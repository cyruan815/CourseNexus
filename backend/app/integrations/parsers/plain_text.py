from __future__ import annotations

import re
from pathlib import Path

from app.core.errors import CourseNexusError
from app.integrations.parsers.base import ParseDiagnostics, ParsedChunk, ParsedDocument


class PlainTextParser:
    def parse(self, file_path: Path) -> ParsedDocument:
        extension = file_path.suffix.lower()
        if extension not in {".txt", ".md"}:
            raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise CourseNexusError(
                code="UNSUPPORTED_FILE_TYPE",
                message="文件类型不支持或无法按 UTF-8 解码",
                status_code=415,
            ) from exc
        except OSError as exc:
            raise CourseNexusError(code="PARSE_FAILED", message="资料文件读取失败", status_code=500) from exc

        chunks = self._parse_markdown(text) if extension == ".md" else self._parse_text(text)
        return ParsedDocument(
            chunks=chunks,
            diagnostics=ParseDiagnostics(
                parser="plain_text",
                profile="text",
                conversion_status="success",
            ),
        )

    def _parse_text(self, text: str) -> list[ParsedChunk]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        return [
            ParsedChunk(chunk_index=index, content_text=paragraph)
            for index, paragraph in enumerate(paragraphs)
        ]

    def _parse_markdown(self, text: str) -> list[ParsedChunk]:
        chunks: list[ParsedChunk] = []
        current_heading: str | None = None
        buffer: list[str] = []

        def flush_buffer() -> None:
            nonlocal buffer
            content_text = "\n".join(line for line in buffer).strip()
            if content_text:
                chunks.append(
                    ParsedChunk(
                        chunk_index=len(chunks),
                        content_text=content_text,
                        heading=current_heading,
                    )
                )
            buffer = []

        for line in text.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                flush_buffer()
                current_heading = stripped_line.lstrip("#").strip() or None
                continue
            if not stripped_line:
                flush_buffer()
                continue
            buffer.append(stripped_line)

        flush_buffer()
        return chunks
