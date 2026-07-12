from __future__ import annotations

from app.integrations.parsers.base import ParsedDocument
from app.integrations.parsers.plain_text import PlainTextParser


def test_parsed_document_keeps_backward_compatible_unknown_diagnostics() -> None:
    parsed = ParsedDocument(chunks=[])

    assert parsed.diagnostics.parser == "unknown"
    assert parsed.diagnostics.profile == "unknown"
    assert parsed.diagnostics.conversion_status == "unknown"
    assert parsed.diagnostics.page_count is None
    assert parsed.diagnostics.warnings == ()


def test_plain_text_parser_splits_txt_into_ordered_chunks(tmp_path) -> None:
    file_path = tmp_path / "notes.txt"
    file_path.write_text("first paragraph\n\nsecond paragraph\n", encoding="utf-8")

    parsed = PlainTextParser().parse(file_path)

    assert [chunk.chunk_index for chunk in parsed.chunks] == [0, 1]
    assert [chunk.content_text for chunk in parsed.chunks] == ["first paragraph", "second paragraph"]
    assert [chunk.heading for chunk in parsed.chunks] == [None, None]


def test_plain_text_parser_records_markdown_heading_for_chunks(tmp_path) -> None:
    file_path = tmp_path / "notes.md"
    file_path.write_text("# Intro\nAlpha\n\n## Details\nBeta\n", encoding="utf-8")

    parsed = PlainTextParser().parse(file_path)

    assert [chunk.content_text for chunk in parsed.chunks] == ["Alpha", "Beta"]
    assert [chunk.heading for chunk in parsed.chunks] == ["Intro", "Details"]


def test_plain_text_parser_marks_successful_text_as_complete(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("Alpha\n\nBeta", encoding="utf-8")

    parsed = PlainTextParser().parse(source)

    assert parsed.diagnostics.parser == "plain_text"
    assert parsed.diagnostics.profile == "text"
    assert parsed.diagnostics.conversion_status == "success"
    assert parsed.diagnostics.page_count is None
    assert parsed.diagnostics.failed_pages == ()
    assert parsed.diagnostics.warnings == ()
