from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.errors import CourseNexusError
from app.integrations.parsers.docling_parser import DoclingParser


class FakeConverter:
    def __init__(self, *, document: object | None = None, error: Exception | None = None) -> None:
        self.document = document or FakeDoclingDocument()
        self.error = error
        self.converted_path: Path | None = None

    def convert(self, file_path: Path):
        self.converted_path = file_path
        if self.error is not None:
            raise self.error
        return SimpleNamespace(document=self.document)


class FakeDoclingDocument:
    pass


class FakeChunker:
    def __init__(self, chunks: list[FakeChunk]) -> None:
        self.chunks = chunks
        self.chunked_document: object | None = None

    def chunk(self, *, dl_doc: object):
        self.chunked_document = dl_doc
        return self.chunks


class FakeChunk:
    def __init__(self, text: str, *, headings: list[str] | None = None, page_no: int | None = None) -> None:
        provenance = []
        if page_no is not None:
            provenance.append(SimpleNamespace(page_no=page_no))
        doc_item = SimpleNamespace(prov=provenance)
        self.text = text
        self.meta = SimpleNamespace(headings=headings or [], doc_items=[doc_item])


def test_docling_parser_maps_order_heading_and_page() -> None:
    document = FakeDoclingDocument()
    converter = FakeConverter(document=document)
    chunker = FakeChunker(
        [
            FakeChunk("Eigenvectors", headings=["Week 2"], page_no=3),
            FakeChunk("Diagonalization", headings=["Week 2"], page_no=4),
        ]
    )

    parsed = DoclingParser(converter=converter, chunker=chunker).parse(Path("slides.pdf"))

    assert converter.converted_path == Path("slides.pdf")
    assert chunker.chunked_document is document
    assert [chunk.chunk_index for chunk in parsed.chunks] == [0, 1]
    assert [chunk.content_text for chunk in parsed.chunks] == ["Eigenvectors", "Diagonalization"]
    assert parsed.chunks[0].heading == "Week 2"
    assert parsed.chunks[0].page == "3"
    assert parsed.chunks[0].page_index == 2


def test_docling_parser_discards_empty_chunks() -> None:
    parsed = DoclingParser(
        converter=FakeConverter(),
        chunker=FakeChunker([FakeChunk("  "), FakeChunk("Kept")]),
    ).parse(Path("slides.pdf"))

    assert [chunk.content_text for chunk in parsed.chunks] == ["Kept"]
    assert parsed.chunks[0].chunk_index == 0


def test_docling_parser_maps_empty_conversion_to_parse_failed() -> None:
    parser = DoclingParser(converter=FakeConverter(), chunker=FakeChunker([FakeChunk("  ")]))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(Path("slides.pdf"))

    assert exc_info.value.code == "PARSE_FAILED"


def test_docling_parser_maps_exceptions_to_parse_failed() -> None:
    parser = DoclingParser(converter=FakeConverter(error=RuntimeError("boom")), chunker=FakeChunker([]))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(Path("slides.pdf"))

    assert exc_info.value.code == "PARSE_FAILED"
