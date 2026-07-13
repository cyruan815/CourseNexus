from __future__ import annotations

import re
import textwrap
from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.modules.generated_content.schemas import GeneratedContentCitationRead, GeneratedContentRead
from app.modules.generation.generators.handout.schemas import HandoutContent, HandoutSection
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestQuestion

ContentJSON = dict[str, Any] | list[Any] | None
PDFLine = tuple[str, int]

PAGE_WIDTH = 595
PAGE_HEIGHT = 842
PAGE_MARGIN_X = 50
PAGE_TOP_Y = 790
PAGE_BOTTOM_Y = 52


def render_task_test_markdown(content: GeneratedContentRead) -> str:
    task_test = _validate_task_test_content(content.content_json)
    citations_by_id = {citation.id: citation for citation in content.source_citations}
    lines: list[str] = [
        f"# {content.title}",
        "",
        "## Instructions",
        "",
        task_test.instructions,
        "",
        "## Questions",
    ]

    for index, question in enumerate(sorted(task_test.questions, key=lambda item: item.sort_order), start=1):
        lines.extend(_render_question(index, question, citations_by_id))

    return "\n".join(lines).rstrip() + "\n"


def render_handout_pdf(content: GeneratedContentRead) -> bytes:
    handout = _validate_handout_content(content.content_json)
    citations_by_id = {citation.id: citation for citation in content.source_citations}
    lines = _render_handout_pdf_lines(content.title, handout, citations_by_id)
    return _build_pdf(lines)


def _validate_task_test_content(content_json: ContentJSON) -> TaskTestContent:
    if not isinstance(content_json, dict):
        raise _invalid_content_error()
    try:
        return TaskTestContent.model_validate(content_json)
    except ValidationError as exc:
        raise _invalid_content_error() from exc


def _validate_handout_content(content_json: ContentJSON) -> HandoutContent:
    if not isinstance(content_json, dict):
        raise _invalid_content_error()
    try:
        return HandoutContent.model_validate(content_json)
    except ValidationError as exc:
        raise _invalid_content_error() from exc


def _render_question(
    index: int,
    question: TaskTestQuestion,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> list[str]:
    lines = [
        "",
        f"### {index}. {question.question_text}",
        "",
    ]
    for option in question.options:
        lines.append(f"- {option.id}. {option.text}")
    if question.options:
        lines.append("")
    lines.extend(
        [
            f"Answer: {_format_answer(question.correct_answer)}",
            "",
            f"Explanation: {question.explanation}",
            "",
        ]
    )
    lines.extend(_render_sources(question.source_citation_ids, citations_by_id))
    return lines


def _format_answer(answer: str | bool | list[str]) -> str:
    if isinstance(answer, bool):
        return "True" if answer else "False"
    if isinstance(answer, list):
        return ", ".join(answer)
    return answer


def _render_sources(
    source_citation_ids: list[str],
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> list[str]:
    citations = _lookup_citations(source_citation_ids, citations_by_id)
    if not citations:
        return ["Sources: unavailable"]

    lines = ["Sources:"]
    for citation in citations:
        lines.append(f"- {_format_citation(citation)}")
    return lines


def _render_handout_pdf_lines(
    title: str,
    handout: HandoutContent,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> list[PDFLine]:
    lines: list[PDFLine] = []
    _append_wrapped(lines, title, font_size=16, max_chars=36)
    _append_blank(lines)
    _append_wrapped(lines, "Overview", font_size=13, max_chars=48)
    _append_wrapped(lines, handout.overview)
    _append_blank(lines)
    _append_wrapped(lines, "Learning Objectives", font_size=13, max_chars=48)
    for objective in handout.learning_objectives:
        _append_wrapped(lines, objective, prefix="- ")
    _append_blank(lines)
    _append_wrapped(lines, "Sections", font_size=13, max_chars=48)
    for index, section in enumerate(sorted(handout.sections, key=lambda item: item.sort_order), start=1):
        _append_section(lines, index, section, citations_by_id)
    _append_blank(lines)
    _append_wrapped(lines, "Summary", font_size=13, max_chars=48)
    _append_wrapped(lines, handout.summary)
    return lines


def _append_section(
    lines: list[PDFLine],
    index: int,
    section: HandoutSection,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> None:
    _append_blank(lines)
    _append_wrapped(lines, f"{index}. {section.title}", font_size=12, max_chars=56)
    _append_wrapped(lines, section.body)
    _append_wrapped(lines, "Key Points", font_size=11, max_chars=60)
    for point in section.key_points:
        _append_wrapped(lines, point, prefix="- ")
    citations = _lookup_citations(section.source_citation_ids, citations_by_id)
    if not citations:
        _append_wrapped(lines, "Sources: unavailable", font_size=9, max_chars=78)
        return
    _append_wrapped(lines, "Sources:", font_size=9, max_chars=78)
    for citation in citations:
        _append_wrapped(lines, _format_citation(citation), font_size=9, max_chars=78, prefix="- ")


def _lookup_citations(
    source_citation_ids: list[str],
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> list[GeneratedContentCitationRead]:
    return [citations_by_id[citation_id] for citation_id in source_citation_ids if citation_id in citations_by_id]


def _format_citation(citation: GeneratedContentCitationRead) -> str:
    return f"{citation.material_name}, {_format_location(citation)}: {citation.hit_text}"


def _format_location(citation: GeneratedContentCitationRead) -> str:
    if citation.page:
        return f"p.{citation.page}"
    if citation.page_index is not None:
        return f"p.{citation.page_index}"
    return "p.unknown"


def _append_blank(lines: list[PDFLine]) -> None:
    lines.append(("", 10))


def _append_wrapped(
    lines: list[PDFLine],
    text: str,
    *,
    font_size: int = 10,
    max_chars: int = 72,
    prefix: str = "",
) -> None:
    cleaned = _clean_text(text)
    if not cleaned:
        _append_blank(lines)
        return
    wrapper = textwrap.TextWrapper(
        width=max_chars,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
        drop_whitespace=True,
    )
    wrapped = wrapper.wrap(cleaned) or [""]
    continuation_prefix = " " * len(prefix)
    for index, segment in enumerate(wrapped):
        line_prefix = prefix if index == 0 else continuation_prefix
        lines.append((f"{line_prefix}{segment}", font_size))


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _build_pdf(lines: list[PDFLine]) -> bytes:
    pages = _paginate_pdf_lines(lines)
    page_object_ids = [6 + index * 2 for index in range(len(pages))]
    content_object_ids = [object_id + 1 for object_id in page_object_ids]
    objects: list[tuple[int, bytes]] = [
        (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
        (2, _pages_object(page_object_ids)),
        (3, _font_object()),
        (4, _cid_font_object()),
        (5, _latin_font_object()),
    ]
    for page_lines, page_object_id, content_object_id in zip(pages, page_object_ids, content_object_ids, strict=True):
        objects.append((page_object_id, _page_object(content_object_id)))
        objects.append((content_object_id, _content_stream_object(page_lines)))
    return _serialize_pdf(objects)


def _paginate_pdf_lines(lines: list[PDFLine]) -> list[list[PDFLine]]:
    pages: list[list[PDFLine]] = [[]]
    cursor_y = PAGE_TOP_Y
    for text, font_size in lines:
        leading = _line_leading(font_size)
        if pages[-1] and cursor_y - leading < PAGE_BOTTOM_Y:
            pages.append([])
            cursor_y = PAGE_TOP_Y
        pages[-1].append((text, font_size))
        cursor_y -= leading
    return pages


def _pages_object(page_object_ids: list[int]) -> bytes:
    kids = " ".join(f"{object_id} 0 R" for object_id in page_object_ids)
    return f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>".encode("ascii")


def _font_object() -> bytes:
    return (
        b"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        b"/Encoding /UniGB-UCS2-H /DescendantFonts [4 0 R] >>"
    )


def _cid_font_object() -> bytes:
    return (
        b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> /DW 1000 >>"
    )


def _latin_font_object() -> bytes:
    return b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"

def _page_object(content_object_id: int) -> bytes:
    return (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
        f"/Resources << /Font << /F1 3 0 R /F2 5 0 R >> >> /Contents {content_object_id} 0 R >>"
    ).encode("ascii")


def _content_stream_object(lines: list[PDFLine]) -> bytes:
    commands = ["BT", f"{PAGE_MARGIN_X} {PAGE_TOP_Y} Td"]
    current_font: tuple[str, int] | None = None
    for text, font_size in lines:
        for font_name, segment in _font_segments(text):
            font = (font_name, font_size)
            if font != current_font:
                commands.append(f"/{font_name} {font_size} Tf")
                current_font = font
            commands.append(f"{_pdf_text_operand(segment, font_name)} Tj")
        commands.append(f"0 -{_line_leading(font_size)} Td")
    commands.append("ET")
    stream = ("\n".join(commands) + "\n").encode("ascii")
    return b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream"


def _font_segments(text: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    current_font: str | None = None
    chars: list[str] = []
    for char in text:
        font_name = "F2" if _is_latin_pdf_char(char) else "F1"
        if current_font is not None and font_name != current_font:
            segments.append((current_font, "".join(chars)))
            chars = []
        current_font = font_name
        chars.append(char)
    if current_font is not None:
        segments.append((current_font, "".join(chars)))
    return segments


def _is_latin_pdf_char(char: str) -> bool:
    return " " <= char <= "~"


def _pdf_text_operand(text: str, font_name: str) -> str:
    cleaned = "".join(char if char >= " " else " " for char in text)
    encoding = "cp1252" if font_name == "F2" else "utf-16-be"
    return "<" + cleaned.encode(encoding, errors="replace").hex().upper() + ">"


def _line_leading(font_size: int) -> int:
    if font_size >= 16:
        return 22
    if font_size >= 13:
        return 18
    if font_size >= 11:
        return 16
    if font_size >= 10:
        return 14
    return 12


def _serialize_pdf(objects: list[tuple[int, bytes]]) -> bytes:
    object_count = max(object_id for object_id, _ in objects)
    payload = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (object_count + 1)
    for object_id, body in sorted(objects, key=lambda item: item[0]):
        offsets[object_id] = len(payload)
        payload.extend(f"{object_id} 0 obj\n".encode("ascii"))
        payload.extend(body)
        payload.extend(b"\nendobj\n")
    xref_offset = len(payload)
    payload.extend(f"xref\n0 {object_count + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        f"trailer\n<< /Size {object_count + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(payload)


def _invalid_content_error() -> CourseNexusError:
    return CourseNexusError(
        code="EXPORT_CONTENT_INVALID",
        message="生成内容结构不支持导出",
        status_code=500,
    )
