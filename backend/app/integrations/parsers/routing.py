from __future__ import annotations

from pathlib import Path

from app.core.errors import CourseNexusError
from app.integrations.parsers.base import ParsedDocument, Parser


PLAIN_TEXT_EXTENSIONS = {".txt", ".md"}
DOCLING_EXTENSIONS = {".pdf", ".docx", ".pptx", ".png", ".jpg", ".jpeg"}


class RoutingParser:
    def __init__(self, *, plain_text: Parser, docling: Parser) -> None:
        self.plain_text = plain_text
        self.docling = docling

    def parse(self, file_path: Path) -> ParsedDocument:
        suffix = file_path.suffix.lower()
        if suffix in PLAIN_TEXT_EXTENSIONS:
            return self.plain_text.parse(file_path)
        if suffix in DOCLING_EXTENSIONS:
            return self.docling.parse(file_path)
        raise CourseNexusError(code="UNSUPPORTED_FILE_TYPE", message="文件类型不支持", status_code=415)
