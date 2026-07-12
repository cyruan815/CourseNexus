from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.errors import CourseNexusError
from app.integrations.parsers.docling_parser import DoclingParser, _pdf_pipeline_options


class FakeConverter:
    def __init__(
        self,
        *,
        document: object | None = None,
        status: str = "success",
        errors: list[object] | None = None,
        page_count: int = 1,
        error: Exception | None = None,
    ) -> None:
        self.document = document if document is not None else FakeDoclingDocument()
        self.status = status
        self.errors = errors or []
        self.page_count = page_count
        self.error = error
        self.converted_source: object | None = None
        self.convert_calls: list[dict[str, object]] = []

    def convert(self, source: object, **kwargs: object):
        self.converted_source = source
        self.convert_calls.append({"source": source, **kwargs})
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            document=self.document,
            status=SimpleNamespace(value=self.status),
            errors=self.errors,
            pages=[SimpleNamespace(page_no=value) for value in range(1, self.page_count + 1)],
            input=SimpleNamespace(page_count=self.page_count),
        )


class FakeDoclingDocument:
    def __init__(self, page_nos: list[int] | None = None) -> None:
        self.items = [SimpleNamespace(prov=[SimpleNamespace(page_no=page_no)]) for page_no in page_nos or []]

    def iterate_items(self):
        return ((item, 0) for item in self.items)


class NullDocumentConverter:
    def convert(self, source: object, **kwargs: object):
        return SimpleNamespace(document=None)


class FakeChunker:
    def __init__(self, chunks: list[FakeChunk]) -> None:
        self.chunks = chunks
        self.chunked_document: object | None = None

    def chunk(self, *, dl_doc: object):
        self.chunked_document = dl_doc
        return self.chunks


class SequentialFakeChunker:
    def __init__(self, chunk_runs: list[list[FakeChunk]]) -> None:
        self.chunk_runs = list(chunk_runs)

    def chunk(self, *, dl_doc: object) -> list[FakeChunk]:
        return self.chunk_runs.pop(0)


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


def test_docling_parser_preserves_partial_result_and_failed_pages(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    error = SimpleNamespace(
        page_no=17,
        module_name="rapidocr",
        error_message="bad allocation",
    )
    converter = FakeConverter(
        document=FakeDoclingDocument(page_nos=[16]),
        status="partial_success",
        errors=[error],
        page_count=59,
    )
    parser = DoclingParser(
        converter=converter,
        chunker=FakeChunker([FakeChunk("Kept", page_no=16)]),
    )

    parsed = parser.parse(source)

    assert [chunk.content_text for chunk in parsed.chunks] == ["Kept"]
    assert parsed.diagnostics.conversion_status == "partial_success"
    assert parsed.diagnostics.page_count == 59
    assert parsed.diagnostics.processed_pages == tuple(range(1, 60))
    assert parsed.diagnostics.pages_with_content == (16,)
    assert parsed.diagnostics.pages_with_chunks == (16,)
    assert parsed.diagnostics.failed_pages == (17,)
    assert parsed.diagnostics.warnings[0].code == "OCR_MEMORY_ERROR"
    assert parsed.diagnostics.warnings[0].page_no == 17


def test_pdf_retries_with_low_resource_ocr_only_when_text_first_is_empty(tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    text_converter = FakeConverter(page_count=2)
    ocr_converter = FakeConverter(page_count=2)
    parser = DoclingParser(
        pdf_converter=text_converter,
        ocr_converter=ocr_converter,
        chunker=SequentialFakeChunker(
            [
                [FakeChunk("  ")],
                [FakeChunk("OCR text", page_no=2)],
            ]
        ),
    )

    parsed = parser.parse(source)

    assert len(text_converter.convert_calls) == 1
    assert len(ocr_converter.convert_calls) == 1
    assert parsed.diagnostics.profile == "pdf_ocr_fallback"
    assert parsed.diagnostics.warnings[-1].code == "OCR_FALLBACK_USED"
    assert parsed.diagnostics.warnings[-1].severity == "info"
    assert [chunk.content_text for chunk in parsed.chunks] == ["OCR text"]


def test_pdf_does_not_run_ocr_when_text_first_has_chunks(tmp_path: Path) -> None:
    source = tmp_path / "slides.pdf"
    source.write_bytes(b"%PDF-1.7\ncontent")
    text_converter = FakeConverter(page_count=2)
    ocr_converter = FakeConverter(page_count=2)
    parser = DoclingParser(
        pdf_converter=text_converter,
        ocr_converter=ocr_converter,
        chunker=FakeChunker([FakeChunk("Native text", page_no=1)]),
    )

    parsed = parser.parse(source)

    assert [chunk.content_text for chunk in parsed.chunks] == ["Native text"]
    assert parsed.diagnostics.profile == "pdf_text_first"
    assert len(text_converter.convert_calls) == 1
    assert ocr_converter.convert_calls == []


def test_pdf_pipeline_options_use_low_memory_defaults() -> None:
    text_options = _pdf_pipeline_options(do_ocr=False)
    ocr_options = _pdf_pipeline_options(do_ocr=True)

    assert text_options.do_ocr is False
    assert text_options.force_backend_text is True
    assert text_options.do_table_structure is False
    assert ocr_options.do_ocr is True
    assert ocr_options.force_backend_text is False
    for options in (text_options, ocr_options):
        assert options.ocr_batch_size == 1
        assert options.layout_batch_size == 1
        assert options.table_batch_size == 1
        assert options.queue_max_size == 4
        assert options.accelerator_options.num_threads == 1
        assert str(options.accelerator_options.device) in {"cpu", "AcceleratorDevice.CPU"}
