from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from pathlib import Path
from typing import Any

import tiktoken
from docling.datamodel.base_models import DocumentStream, InputFormat
from docling.datamodel.pipeline_options import AcceleratorDevice, AcceleratorOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

from app.core.errors import CourseNexusError
from app.integrations.parsers.base import ParseDiagnostics, ParseWarning, ParsedChunk, ParsedDocument


def _pdf_pipeline_options(*, do_ocr: bool) -> PdfPipelineOptions:
    options = PdfPipelineOptions()
    options.do_ocr = do_ocr
    options.force_backend_text = not do_ocr
    options.do_table_structure = False
    options.ocr_batch_size = 1
    options.layout_batch_size = 1
    options.table_batch_size = 1
    options.queue_max_size = 4
    options.accelerator_options = AcceleratorOptions(
        num_threads=1,
        device=AcceleratorDevice.CPU,
    )
    return options


def _pdf_converter(*, do_ocr: bool) -> DocumentConverter:
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=_pdf_pipeline_options(do_ocr=do_ocr),
            )
        }
    )


class DoclingParser:
    def __init__(
        self,
        *,
        max_tokens: int = 800,
        converter: Any | None = None,
        pdf_converter: Any | None = None,
        ocr_converter: Any | None = None,
        chunker: Any | None = None,
    ) -> None:
        self.injected_converter = converter
        self.default_converter = converter
        self.pdf_converter = pdf_converter
        self.ocr_converter = ocr_converter
        self.chunker = chunker or HybridChunker(
            tokenizer=OpenAITokenizer(
                tokenizer=tiktoken.get_encoding("cl100k_base"),
                max_tokens=max_tokens,
            ),
            merge_peers=True,
        )

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            if self.injected_converter is not None:
                parsed = self._convert(file_path, converter=self.injected_converter, profile="injected")
            elif file_path.suffix.lower() == ".pdf":
                parsed = self._parse_pdf(file_path)
            else:
                parsed = self._convert(
                    file_path,
                    converter=self._standard_converter(),
                    profile="docling_default",
                )
            if not parsed.chunks:
                raise CourseNexusError(code="PARSE_FAILED", message="资料解析结果为空", status_code=500)
            return parsed
        except CourseNexusError:
            raise
        except Exception as exc:
            raise CourseNexusError(code="PARSE_FAILED", message="资料解析失败", status_code=500) from exc

    def _parse_pdf(self, file_path: Path) -> ParsedDocument:
        text_result = self._convert(
            file_path,
            converter=self._text_pdf_converter(),
            profile="pdf_text_first",
        )
        if text_result.chunks:
            return text_result

        ocr_result = self._convert(
            file_path,
            converter=self._fallback_ocr_converter(),
            profile="pdf_ocr_fallback",
        )
        fallback_warning = ParseWarning(
            code="OCR_FALLBACK_USED",
            message="PDF 文本层为空，已使用低资源 OCR 重试",
            severity="info",
        )
        combined_warnings = text_result.diagnostics.warnings + ocr_result.diagnostics.warnings + (fallback_warning,)
        combined_failed_pages = tuple(
            sorted(set(text_result.diagnostics.failed_pages) | set(ocr_result.diagnostics.failed_pages))
        )
        return replace(
            ocr_result,
            diagnostics=replace(
                ocr_result.diagnostics,
                page_count=ocr_result.diagnostics.page_count or text_result.diagnostics.page_count,
                failed_pages=combined_failed_pages,
                warnings=combined_warnings,
            ),
        )

    def _convert(self, file_path: Path, *, converter: Any, profile: str) -> ParsedDocument:
        conversion = converter.convert(
            self._document_stream_for(file_path),
            raises_on_error=False,
        )
        document = getattr(conversion, "document", None)
        if document is None:
            return ParsedDocument(
                chunks=[],
                diagnostics=ParseDiagnostics(
                    parser="docling",
                    profile=profile,
                    conversion_status="failure",
                    warnings=(
                        ParseWarning(code="DOCLING_STAGE_FAILED", message="文档转换未返回结果"),
                    ),
                ),
            )

        raw_chunks = list(self.chunker.chunk(dl_doc=document))
        chunks = self._parsed_chunks(raw_chunks)
        errors = list(getattr(conversion, "errors", None) or [])
        warnings = tuple(_warning_for_error(error) for error in errors)
        failed_pages = tuple(
            sorted(
                {
                    int(error.page_no)
                    for error in errors
                    if getattr(error, "page_no", None) is not None
                }
            )
        )
        status = getattr(getattr(conversion, "status", None), "value", "unknown")
        page_count = getattr(getattr(conversion, "input", None), "page_count", None)
        processed_pages = tuple(
            sorted(
                int(page.page_no)
                for page in getattr(conversion, "pages", None) or []
                if getattr(page, "page_no", None) is not None
            )
        )
        return ParsedDocument(
            chunks=chunks,
            diagnostics=ParseDiagnostics(
                parser="docling",
                profile=profile,
                conversion_status=str(status),
                page_count=int(page_count) if page_count else None,
                processed_pages=processed_pages,
                pages_with_content=_pages_with_content(document),
                pages_with_chunks=_pages_with_raw_chunks(raw_chunks),
                failed_pages=failed_pages,
                warnings=warnings,
            ),
        )

    def _parsed_chunks(self, raw_chunks: list[Any]) -> list[ParsedChunk]:
        chunks: list[ParsedChunk] = []
        for raw_chunk in raw_chunks:
            text = self._text_for_chunk(raw_chunk)
            if not text:
                continue
            chunks.append(
                ParsedChunk(
                    chunk_index=len(chunks),
                    content_text=text,
                    heading=self._heading_for_chunk(raw_chunk),
                    page=self._page_for_chunk(raw_chunk),
                    page_index=self._page_index_for_chunk(raw_chunk),
                )
            )
        return chunks

    def _standard_converter(self) -> Any:
        if self.default_converter is None:
            self.default_converter = DocumentConverter()
        return self.default_converter

    def _text_pdf_converter(self) -> Any:
        if self.pdf_converter is None:
            self.pdf_converter = _pdf_converter(do_ocr=False)
        return self.pdf_converter

    def _fallback_ocr_converter(self) -> Any:
        if self.ocr_converter is None:
            self.ocr_converter = _pdf_converter(do_ocr=True)
        return self.ocr_converter

    def _document_stream_for(self, file_path: Path) -> DocumentStream:
        extension = file_path.suffix.lower() or ".bin"
        return DocumentStream(
            name=f"source{extension}",
            stream=BytesIO(file_path.read_bytes()),
        )

    def _text_for_chunk(self, chunk: Any) -> str:
        return str(getattr(chunk, "text", "") or "").strip()

    def _heading_for_chunk(self, chunk: Any) -> str | None:
        meta = getattr(chunk, "meta", None)
        headings = getattr(meta, "headings", None) or []
        if not headings:
            return None
        heading = str(headings[0]).strip()
        return heading or None

    def _page_for_chunk(self, chunk: Any) -> str | None:
        page_no = self._page_no_for_chunk(chunk)
        return str(page_no) if page_no is not None else None

    def _page_index_for_chunk(self, chunk: Any) -> int | None:
        page_no = self._page_no_for_chunk(chunk)
        return page_no - 1 if page_no is not None else None

    def _page_no_for_chunk(self, chunk: Any) -> int | None:
        page_nos = _page_nos_for_raw_chunk(chunk)
        return page_nos[0] if page_nos else None


def _warning_for_error(error: Any) -> ParseWarning:
    raw_message = str(getattr(error, "error_message", "") or "")
    normalized = raw_message.lower()
    code = (
        "OCR_MEMORY_ERROR"
        if "bad_alloc" in normalized or "bad allocation" in normalized
        else "DOCLING_STAGE_FAILED"
    )
    return ParseWarning(
        code=code,
        message="OCR 内存分配失败" if code == "OCR_MEMORY_ERROR" else "文档页面处理失败",
        page_no=getattr(error, "page_no", None),
        component=str(getattr(error, "module_name", "") or "") or None,
    )


def _page_nos_for_item(item: Any) -> tuple[int, ...]:
    return tuple(
        sorted(
            {
                int(provenance.page_no)
                for provenance in getattr(item, "prov", None) or []
                if getattr(provenance, "page_no", None) is not None
            }
        )
    )


def _page_nos_for_raw_chunk(raw_chunk: Any) -> tuple[int, ...]:
    pages: set[int] = set()
    meta = getattr(raw_chunk, "meta", None)
    for item in getattr(meta, "doc_items", None) or []:
        pages.update(_page_nos_for_item(item))
    return tuple(sorted(pages))


def _pages_with_content(document: Any) -> tuple[int, ...]:
    iterate_items = getattr(document, "iterate_items", None)
    if not callable(iterate_items):
        return ()
    pages: set[int] = set()
    for item, _level in iterate_items():
        pages.update(_page_nos_for_item(item))
    return tuple(sorted(pages))


def _pages_with_raw_chunks(raw_chunks: list[Any]) -> tuple[int, ...]:
    pages: set[int] = set()
    for raw_chunk in raw_chunks:
        pages.update(_page_nos_for_raw_chunk(raw_chunk))
    return tuple(sorted(pages))
