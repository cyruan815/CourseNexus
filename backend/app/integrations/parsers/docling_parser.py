from __future__ import annotations

from pathlib import Path
from typing import Any

import tiktoken
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

from app.core.errors import CourseNexusError
from app.integrations.parsers.base import ParsedChunk, ParsedDocument


class DoclingParser:
    def __init__(self, *, max_tokens: int = 800, converter: Any | None = None, chunker: Any | None = None) -> None:
        self.converter = converter or DocumentConverter()
        self.chunker = chunker or HybridChunker(
            tokenizer=OpenAITokenizer(
                tokenizer=tiktoken.get_encoding("cl100k_base"),
                max_tokens=max_tokens,
            ),
            merge_peers=True,
        )

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            conversion = self.converter.convert(file_path)
            document = getattr(conversion, "document", None)
            if document is None:
                raise ValueError("Docling conversion did not return a document")

            chunks: list[ParsedChunk] = []
            for raw_chunk in self.chunker.chunk(dl_doc=document):
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
            if not chunks:
                raise CourseNexusError(code="PARSE_FAILED", message="资料解析结果为空", status_code=500)
            return ParsedDocument(chunks=chunks)
        except CourseNexusError:
            raise
        except Exception as exc:
            raise CourseNexusError(code="PARSE_FAILED", message="资料解析失败", status_code=500) from exc

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
        meta = getattr(chunk, "meta", None)
        for doc_item in getattr(meta, "doc_items", None) or []:
            for provenance in getattr(doc_item, "prov", None) or []:
                page_no = getattr(provenance, "page_no", None)
                if page_no is not None:
                    return int(page_no)
        return None
