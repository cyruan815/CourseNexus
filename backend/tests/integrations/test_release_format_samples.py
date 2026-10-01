from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile, is_zipfile

import pytest

from app.integrations.parsers.docling_parser import DoclingParser
from app.integrations.parsers.plain_text import PlainTextParser


SAMPLE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "release_samples"
MANIFEST = json.loads((SAMPLE_ROOT / "manifest.json").read_text(encoding="utf-8"))
ANCHOR_TEXT = MANIFEST["anchor_text"]
OOXML_EXPECTED_PART = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/slides/slide1.xml",
}


@pytest.fixture(scope="module")
def docling_parser() -> DoclingParser:
    return DoclingParser()


def test_release_sample_manifest_covers_each_supported_document_format() -> None:
    samples = MANIFEST["samples"]
    assert MANIFEST["schema_version"] == 1
    assert {Path(sample["file_name"]).suffix for sample in samples} == {
        ".txt",
        ".pdf",
        ".docx",
        ".pptx",
    }
    assert all(sample["media_type"] for sample in samples)
    assert all(sample["parser_kind"] in {"plain_text", "docling"} for sample in samples)


@pytest.mark.parametrize("sample", MANIFEST["samples"], ids=lambda sample: sample["file_name"])
def test_release_sample_is_a_real_safe_file(sample: dict[str, str]) -> None:
    sample_path = SAMPLE_ROOT / sample["file_name"]
    assert sample_path.is_file()
    assert 0 < sample_path.stat().st_size < 256 * 1024

    suffix = sample_path.suffix
    if suffix == ".txt":
        assert ANCHOR_TEXT in sample_path.read_text(encoding="utf-8")
        return
    if suffix == ".pdf":
        payload = sample_path.read_bytes()
        assert payload.startswith(b"%PDF-")
        assert payload.rstrip().endswith(b"%%EOF")
        assert b"/Encrypt" not in payload
        assert b"/JavaScript" not in payload
        return

    assert suffix in OOXML_EXPECTED_PART
    assert is_zipfile(sample_path)
    with ZipFile(sample_path) as package:
        names = set(package.namelist())
        assert "[Content_Types].xml" in names
        assert OOXML_EXPECTED_PART[suffix] in names
        assert not any(name.lower().endswith("vbaproject.bin") for name in names)
        relationships = b"".join(
            package.read(name) for name in names if name.lower().endswith(".rels")
        )
        assert b'TargetMode="External"' not in relationships


@pytest.mark.parametrize("sample", MANIFEST["samples"], ids=lambda sample: sample["file_name"])
def test_production_parser_extracts_shared_anchor(
    sample: dict[str, str],
    docling_parser: DoclingParser,
) -> None:
    sample_path = SAMPLE_ROOT / sample["file_name"]
    parser = PlainTextParser() if sample["parser_kind"] == "plain_text" else docling_parser

    parsed = parser.parse(sample_path)

    assert parsed.chunks
    assert ANCHOR_TEXT in " ".join(chunk.content_text for chunk in parsed.chunks)
    assert parsed.diagnostics.conversion_status in {"success", "unknown"}
