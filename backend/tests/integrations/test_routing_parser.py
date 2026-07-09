from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import CourseNexusError
from app.integrations.parsers.base import ParsedDocument
from app.integrations.parsers.routing import RoutingParser


class RecordingParser:
    def __init__(self, name: str) -> None:
        self.name = name
        self.called = False

    def parse(self, file_path: Path) -> ParsedDocument:
        self.called = True
        return ParsedDocument(chunks=[])


def test_routing_parser_selects_docling_for_pdf(tmp_path: Path) -> None:
    plain = RecordingParser("plain")
    docling = RecordingParser("docling")
    parser = RoutingParser(plain_text=plain, docling=docling)

    parser.parse(tmp_path / "slides.pdf")

    assert docling.called is True
    assert plain.called is False


@pytest.mark.parametrize("filename", ["notes.txt", "notes.md"])
def test_routing_parser_selects_plain_text_for_text_files(tmp_path: Path, filename: str) -> None:
    plain = RecordingParser("plain")
    docling = RecordingParser("docling")
    parser = RoutingParser(plain_text=plain, docling=docling)

    parser.parse(tmp_path / filename)

    assert plain.called is True
    assert docling.called is False


@pytest.mark.parametrize("filename", ["slides.pdf", "notes.docx", "deck.pptx", "image.png", "photo.jpg", "photo.jpeg"])
def test_routing_parser_selects_docling_for_complex_files(tmp_path: Path, filename: str) -> None:
    plain = RecordingParser("plain")
    docling = RecordingParser("docling")
    parser = RoutingParser(plain_text=plain, docling=docling)

    parser.parse(tmp_path / filename)

    assert docling.called is True
    assert plain.called is False


def test_routing_parser_rejects_unknown_extension(tmp_path: Path) -> None:
    parser = RoutingParser(plain_text=RecordingParser("plain"), docling=RecordingParser("docling"))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(tmp_path / "archive.zip")

    assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"
