from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.errors import CourseNexusError
from app.integrations.parsers.docling_parser import DoclingParser


class FakeConverter:
    def __init__(self, *, document: object | None = None, error: Exception | None = None) -> None:
        self.document = document if document is not None else FakeDoclingDocument()
        self.error = error
        self.converted_source: object | None = None

    def convert(self, source: object):
        self.converted_source = source
        if self.error is not None:
            raise self.error
        return SimpleNamespace(document=self.document)


class FakeDoclingDocument:
    pass


class NullDocumentConverter:
    def convert(self, source: object):
        return SimpleNamespace(document=None)


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


def test_docling_parser_maps_order_heading_and_page(tmp_path: Path) -> None:
    document = FakeDoclingDocument()
    converter = FakeConverter(document=document)
    chunker = FakeChunker(
        [
            FakeChunk("Eigenvectors", headings=["Week 2"], page_no=3),
            FakeChunk("Diagonalization", headings=["Week 2"], page_no=4),
        ]
    )

    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")

    parsed = DoclingParser(converter=converter, chunker=chunker).parse(source)

    assert getattr(converter.converted_source, "name") == "source.pdf"
    assert chunker.chunked_document is document
    assert [chunk.chunk_index for chunk in parsed.chunks] == [0, 1]
    assert [chunk.content_text for chunk in parsed.chunks] == ["Eigenvectors", "Diagonalization"]
    assert parsed.chunks[0].heading == "Week 2"
    assert parsed.chunks[0].page == "3"
    assert parsed.chunks[0].page_index == 2


def test_docling_parser_uses_ascii_document_stream_for_non_ascii_paths(tmp_path: Path) -> None:
    source = tmp_path / "课程资料" / "Chap7 物理层.pdf"
    source.parent.mkdir()
    source.write_bytes(b"%PDF-1.7\ncontent")
    converter = FakeConverter()
    parser = DoclingParser(converter=converter, chunker=FakeChunker([FakeChunk("Kept")]))

    parser.parse(source)

    converted_source = converter.converted_source
    assert getattr(converted_source, "name") == "source.pdf"
    assert converted_source is not source
    assert converted_source.stream.read() == b"%PDF-1.7\ncontent"


def test_docling_parser_discards_empty_chunks(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")

    parsed = DoclingParser(
        converter=FakeConverter(),
        chunker=FakeChunker([FakeChunk("  "), FakeChunk("Kept")]),
    ).parse(source)

    assert [chunk.content_text for chunk in parsed.chunks] == ["Kept"]
    assert parsed.chunks[0].chunk_index == 0


def test_docling_parser_maps_empty_conversion_to_parse_failed(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    parser = DoclingParser(converter=FakeConverter(), chunker=FakeChunker([FakeChunk("  ")]))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(source)

    assert exc_info.value.code == "PARSE_FAILED"


def test_docling_parser_maps_missing_document_to_parse_failed(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    parser = DoclingParser(converter=NullDocumentConverter(), chunker=FakeChunker([]))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(source)

    assert exc_info.value.code == "PARSE_FAILED"


def test_docling_parser_maps_exceptions_to_parse_failed(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    parser = DoclingParser(converter=FakeConverter(error=RuntimeError("boom")), chunker=FakeChunker([]))

    with pytest.raises(CourseNexusError) as exc_info:
        parser.parse(source)

    assert exc_info.value.code == "PARSE_FAILED"
