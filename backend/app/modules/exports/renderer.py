from __future__ import annotations

from collections.abc import Iterable
import html
from pathlib import Path
import re
import textwrap
from tempfile import TemporaryDirectory
from typing import Any

from jinja2 import Environment, select_autoescape
from markdown_it import MarkdownIt
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

_MARKDOWN_CHOICE_OPTION_IDS = ("A", "B", "C", "D")
_MARKDOWN_CHOICE_QUESTION_TYPES = {"single_choice", "multiple_choice"}
_UNSAFE_CITATION_SNIPPET_MARKERS = ("formula-not-decoded", "", "", "")


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
    markdown = content.content.strip() if isinstance(content.content, str) else ""
    if not markdown:
        raise _invalid_content_error()
    return render_markdown_pdf(markdown, title=content.title)


def render_markdown_pdf(markdown: str, *, title: str = "CourseNexus") -> bytes:
    html = render_markdown_pdf_html(markdown, title=title)

    with TemporaryDirectory(prefix="coursenexus-pdf-") as temp_dir:
        html_path = Path(temp_dir) / "document.html"
        pdf_path = Path(temp_dir) / "document.pdf"
        html_path.write_text(html, encoding="utf-8")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for handout PDF export. Run `uv add playwright` and `uv run playwright install chromium`.") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page_errors: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(html_path.as_uri(), wait_until="load")
                page.emulate_media(media="print")
                page.wait_for_function("() => !document.fonts || document.fonts.status === 'loaded'", timeout=30_000)

                render_state = page.evaluate(
                    """
                    () => ({
                      mathErrors: document.querySelectorAll('.katex-error').length
                    })
                    """
                )
                if page_errors:
                    raise RuntimeError("PDF HTML rendering failed: " + "; ".join(page_errors))
                if render_state.get("mathErrors"):
                    raise RuntimeError("PDF HTML rendering produced KaTeX errors")

                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={"top": "16mm", "right": "16mm", "bottom": "18mm", "left": "16mm"},
                )
            finally:
                browser.close()

        return pdf_path.read_bytes()


def render_markdown_pdf_html(markdown: str, *, title: str = "CourseNexus") -> str:
    safe_markdown = _sanitize_markdown_for_pdf(markdown)
    body_html = _render_math_html(_build_markdown_renderer().render(safe_markdown))
    template = _html_environment().from_string(_PDF_HTML_TEMPLATE)
    return template.render(title=title, body_html=body_html, css=_PDF_CSS)


def _build_markdown_renderer() -> MarkdownIt:
    return MarkdownIt(
        "commonmark",
        {
            "html": False,
            "breaks": False,
            "linkify": False,
        },
    ).enable("table")


def _html_environment() -> Environment:
    return Environment(autoescape=select_autoescape(("html", "xml")))


def _render_math_html(body_html: str) -> str:
    return re.sub(r"<p>\$\$\n(.+?)\n\$\$</p>", _math_block_replacement, body_html, flags=re.DOTALL)


def _math_block_replacement(match: re.Match[str]) -> str:
    latex = html.unescape(match.group(1)).strip()
    return f'<div class="math-display"><span class="katex">{_latex_to_readable_html(latex)}</span></div>'


def _latex_to_readable_html(latex: str) -> str:
    readable = latex.strip()
    readable = readable.replace(r"\times", "×")
    readable = readable.replace(r"\cdot", "·")
    readable = readable.replace(r"\leq", "≤")
    readable = readable.replace(r"\geq", "≥")
    readable = readable.replace(r"\approx", "≈")
    readable = readable.replace(r"\log", "log")
    escaped = html.escape(readable)
    escaped = re.sub(r"([A-Za-z])_\{?([A-Za-z0-9]+)\}?", r"\1<sub>\2</sub>", escaped)
    escaped = re.sub(r"([A-Za-z0-9)]+)\^\{?([A-Za-z0-9+\-/]+)\}?", r"\1<sup>\2</sup>", escaped)
    return escaped


def _render_handout_pdf_markdown(
    title: str,
    handout: HandoutContent,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> str:
    if handout.schema_version == 2:
        return _render_handout_v2_markdown(title, handout, citations_by_id)

    lines: list[str] = [
        f"# {title}",
        "",
        _handout_source_notice(handout, citations_by_id),
        "",
        "## 概览",
        "",
        handout.overview,
        "",
        "## 学习目标",
        "",
    ]
    for objective in handout.learning_objectives:
        lines.append(f"- {objective}")
    lines.extend(["", "## 正文"])
    for index, section in enumerate(sorted(handout.sections, key=lambda item: item.sort_order), start=1):
        lines.extend(
            [
                "",
                f"### {index}. {section.title}",
                "",
                section.body,
                "",
                "要点：",
                "",
            ]
        )
        for point in section.key_points:
            lines.append(f"- {point}")
    lines.extend(["", "## 总结", "", handout.summary])
    return _sanitize_markdown_for_pdf("\n".join(lines).rstrip() + "\n")



def _render_handout_v2_markdown(
    title: str,
    handout: HandoutContent,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> str:
    lines: list[str] = [
        f"# {title}",
        "",
        _handout_source_notice(handout, citations_by_id),
        "",
        "## 概览",
        "",
        handout.overview,
        "",
        "## 学习目标",
        "",
    ]
    for objective in handout.learning_objectives:
        lines.append(f"- {objective}")

    if handout.prerequisites:
        lines.extend(["", "## 前置知识"])
        for index, prerequisite in enumerate(
            sorted(handout.prerequisites, key=lambda item: item.sort_order),
            start=1,
        ):
            lines.extend(["", f"### {index}. {prerequisite.title}", "", prerequisite.explanation])
            if prerequisite.example:
                lines.extend(["", f"示例：{prerequisite.example}"])

    if handout.knowledge_map is not None:
        lines.extend(["", "## 知识地图", ""])
        lines.extend(_render_handout_block_markdown(handout.knowledge_map))

    lines.extend(["", "## 正文"])
    for index, section in enumerate(sorted(handout.sections, key=lambda item: item.sort_order), start=1):
        lines.extend(["", f"### {index}. {section.title}"])
        if section.lead:
            lines.extend(["", section.lead])
        for block in section.blocks:
            lines.extend(["", *_render_handout_block_markdown(block)])
        if section.key_points:
            lines.extend(["", "要点：", ""])
            for point in section.key_points:
                lines.append(f"- {point}")

    if handout.formula_cards:
        lines.extend(["", "## 公式卡片"])
        for formula in handout.formula_cards:
            lines.extend(["", *_render_formula_block_markdown(formula, heading_level=3)])

    if handout.exam_focus:
        lines.extend(["", "## 考试重点"])
        for index, item in enumerate(sorted(handout.exam_focus, key=lambda value: value.sort_order), start=1):
            lines.extend(["", f"### {index}. {item.title}", "", item.description])


    lines.extend(["", "## 总结", "", handout.summary])
    return _sanitize_markdown_for_pdf("\n".join(lines).rstrip() + "\n")


def _render_handout_block_markdown(block: object) -> list[str]:
    block_type = getattr(block, "type", "")
    if block_type == "paragraph":
        return [str(getattr(block, "text", "")).strip()]
    if block_type == "formula":
        return _render_formula_block_markdown(block)
    if block_type == "table":
        return _render_table_block_markdown(block)
    if block_type == "mindmap":
        return _render_mindmap_block_markdown(block)
    if block_type == "example":
        return _render_example_block_markdown(block)
    if block_type == "steps":
        return _render_steps_block_markdown(block)
    if block_type == "callout":
        title = str(getattr(block, "title", "")).strip()
        text = str(getattr(block, "text", "")).strip()
        return [f"> **{title}**: {text}"]
    if block_type == "mermaid":
        block_title = str(getattr(block, "title", "")).strip()
        code = str(getattr(block, "code", "")).strip()
        explanation = str(getattr(block, "explanation", "")).strip()
        return [
            f"#### {block_title}",
            "",
            "```mermaid",
            code,
            "```",
            "",
            explanation,
        ]
    if block_type == "chart":
        return _render_chart_block_markdown(block)
    return []


def _render_formula_block_markdown(block: object, *, heading_level: int = 4) -> list[str]:
    block_title = str(getattr(block, "title", "")).strip()
    latex = str(getattr(block, "latex", "")).strip()
    lines = [f"{'#' * heading_level} {block_title}", "", "$$", latex, "$$"]
    purpose = str(getattr(block, "purpose", "")).strip()
    if purpose:
        lines.extend(["", f"用途：{purpose}"])
    variables = list(getattr(block, "variables", []))
    if variables:
        lines.extend(["", "变量："])
        for variable in variables:
            symbol = str(getattr(variable, "symbol", "")).strip()
            meaning = str(getattr(variable, "meaning", "")).strip()
            unit = getattr(variable, "unit", None)
            suffix = f" ({unit})" if unit else ""
            lines.append(f"- `{symbol}`: {meaning}{suffix}")
    _append_optional_bullets(lines, "适用条件", getattr(block, "conditions", []))
    _append_optional_bullets(lines, "限制", getattr(block, "limitations", []))
    return lines


def _render_table_block_markdown(block: object) -> list[str]:
    columns = list(getattr(block, "columns", []))
    rows = list(getattr(block, "rows", []))
    block_title = str(getattr(block, "title", "")).strip()
    headers = [str(getattr(column, "label", "")).strip() for column in columns]
    values = [[_stringify_markdown_value(row.get(getattr(column, "key"), "")) for column in columns] for row in rows]
    return [f"#### {block_title}", "", *_markdown_table(headers, values)]


def _render_mindmap_block_markdown(block: object) -> list[str]:
    block_title = str(getattr(block, "title", "")).strip()
    return [f"#### {block_title}", "", *_render_mindmap_node_markdown(getattr(block, "root"), depth=0)]


def _render_mindmap_node_markdown(node: object, *, depth: int) -> list[str]:
    indent = "  " * depth
    label = str(getattr(node, "label", "")).strip()
    lines = [f"{indent}- {label}"]
    for child in getattr(node, "children", []):
        lines.extend(_render_mindmap_node_markdown(child, depth=depth + 1))
    return lines


def _render_example_block_markdown(block: object) -> list[str]:
    block_title = str(getattr(block, "title", "")).strip()
    problem = str(getattr(block, "problem", "")).strip()
    answer = str(getattr(block, "answer", "")).strip()
    explanation = str(getattr(block, "explanation", "")).strip()
    lines = [f"#### 示例：{block_title}", "", f"题目：{problem}"]
    steps = list(getattr(block, "steps", []))
    if steps:
        lines.extend(["", "步骤："])
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {step}")
    lines.extend(["", f"答案：{answer}", "", f"解析：{explanation}"])
    return lines


def _render_steps_block_markdown(block: object) -> list[str]:
    block_title = str(getattr(block, "title", "")).strip()
    lines = [f"#### {block_title}", ""]
    for index, step in enumerate(getattr(block, "steps", []), start=1):
        lines.append(f"{index}. {step}")
    return lines


def _render_chart_block_markdown(block: object) -> list[str]:
    unit = getattr(block, "unit", None) or ""
    block_title = str(getattr(block, "title", "")).strip()
    explanation = str(getattr(block, "explanation", "")).strip()
    rows: list[list[str]] = []
    for series in getattr(block, "series", []):
        for point in getattr(series, "points", []):
            rows.append([str(getattr(series, "name", "")), str(getattr(point, "label", "")), _stringify_markdown_value(getattr(point, "value", "")), str(unit)])
    return [f"#### {block_title}", "", explanation, "", *_markdown_table(["系列", "标签", "数值", "单位"], rows)]


def _append_optional_bullets(lines: list[str], title: str, values: object) -> None:
    if not isinstance(values, list):
        return
    items = [str(item).strip() for item in values if str(item).strip()]
    if not items:
        return
    lines.extend(["", f"{title}:"])
    for item in items:
        lines.append(f"- {item}")


def _markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    table = ["| " + " | ".join(_markdown_cell(header) for header in headers) + " |"]
    table.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        table.append("| " + " | ".join(_markdown_cell(cell) for cell in row) + " |")
    return table


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>").strip()


def _stringify_markdown_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)

def _sanitize_markdown_for_pdf(markdown: str) -> str:
    sanitized_lines: list[str] = []
    for line in markdown.splitlines():
        cleaned = _sanitize_markdown_line(line)
        if cleaned is not None:
            sanitized_lines.append(cleaned)
    return "\n".join(sanitized_lines).rstrip() + "\n"


def _sanitize_markdown_line(line: str) -> str | None:
    if not any(marker in line for marker in _UNSAFE_CITATION_SNIPPET_MARKERS):
        return line
    citation_match = re.match(r"^(\s*-\s*.+?,\s*p\.[^:]+):", line)
    if citation_match:
        return citation_match.group(1).rstrip()
    return None


_PDF_HTML_TEMPLATE = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>{{ title }}</title>
  <style>{{ css | safe }}</style>
</head>
<body>
  <main id=\"pdf-document\">{{ body_html | safe }}</main>
</body>
</html>
"""

_PDF_CSS = """
@page {
  size: A4;
  margin: 16mm 16mm 18mm;
}

* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  padding: 0;
  width: 100%;
}

body {
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.65;
  color: #222;
  overflow-wrap: anywhere;
  word-break: normal;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

#pdf-document {
  width: 100%;
  max-width: 100%;
}

h1 {
  margin: 0 0 16px;
  font-size: 24pt;
  line-height: 1.25;
}

h2 {
  margin: 24px 0 10px;
  font-size: 16pt;
  line-height: 1.35;
  break-after: avoid-page;
}

h3 {
  margin: 18px 0 8px;
  font-size: 13pt;
  break-after: avoid-page;
}

p {
  margin: 7px 0;
  orphans: 3;
  widows: 3;
}

ul,
ol {
  margin: 8px 0;
  padding-left: 24px;
}

li {
  margin: 4px 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 12px 0;
}

th,
td {
  padding: 7px 8px;
  border: 1px solid #bbb;
  vertical-align: top;
  overflow-wrap: anywhere;
}

pre {
  max-width: 100%;
  padding: 10px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  border: 1px solid #ddd;
  border-radius: 6px;
}

code {
  font-family: Consolas, "JetBrains Mono", monospace;
}

.math-display {
  margin: 12px 0;
  padding: 8px 10px;
  text-align: center;
  overflow-wrap: anywhere;
  border-radius: 4px;
  background: #f7f7f7;
}

.katex {
  font-family: "Cambria Math", "Times New Roman", "Microsoft YaHei", serif;
  font-size: 12pt;
  line-height: 1.5;
}

blockquote {
  margin: 12px 0;
  padding: 8px 12px;
  border-left: 4px solid #888;
  color: #444;
}
"""

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
    option_labels = _choice_option_labels(question)
    for option in question.options:
        option_label = option_labels.get(option.id, option.id)
        lines.append(f"- {option_label}. {option.text}")
    if question.options:
        lines.append("")
    lines.extend(
        [
            f"Answer: {_format_question_answer(question, option_labels)}",
            "",
            f"Explanation: {question.explanation}",
            "",
        ]
    )
    lines.extend(_render_sources(question.source_citation_ids, citations_by_id))
    return lines


def _choice_option_labels(question: TaskTestQuestion) -> dict[str, str]:
    if question.question_type not in _MARKDOWN_CHOICE_QUESTION_TYPES:
        return {}
    if len(question.options) != len(_MARKDOWN_CHOICE_OPTION_IDS):
        return {}
    return {option.id: label for option, label in zip(question.options, _MARKDOWN_CHOICE_OPTION_IDS, strict=True)}


def _format_question_answer(question: TaskTestQuestion, option_labels: dict[str, str]) -> str:
    if option_labels and question.question_type == "single_choice" and isinstance(question.correct_answer, str):
        return option_labels.get(question.correct_answer, question.correct_answer)
    if option_labels and question.question_type == "multiple_choice" and isinstance(question.correct_answer, list):
        return ", ".join(option_labels.get(answer, answer) for answer in question.correct_answer)
    return _format_answer(question.correct_answer)


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
    _append_wrapped(lines, _handout_source_notice(handout, citations_by_id), font_size=10, max_chars=72)
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
        _append_section(lines, index, section)
    _append_blank(lines)
    _append_wrapped(lines, "Summary", font_size=13, max_chars=48)
    _append_wrapped(lines, handout.summary)
    return lines


def _append_section(lines: list[PDFLine], index: int, section: HandoutSection) -> None:
    _append_blank(lines)
    _append_wrapped(lines, f"{index}. {section.title}", font_size=12, max_chars=56)
    _append_wrapped(lines, section.body)
    _append_wrapped(lines, "Key Points", font_size=11, max_chars=60)
    for point in section.key_points:
        _append_wrapped(lines, point, prefix="- ")


def _handout_source_notice(
    handout: HandoutContent,
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> str:
    material_names = _unique_material_names(citations_by_id.values())
    topic_label = _handout_topic_label(handout)
    if material_names:
        materials = "".join(f"《{material_name}》" for material_name in material_names)
        return f"来源说明：本讲义根据{materials}中“{topic_label}”相关内容生成。"
    return f"来源说明：本讲义根据当前任务相关资料中“{topic_label}”相关内容生成。"


def _unique_material_names(citations: Iterable[GeneratedContentCitationRead]) -> list[str]:
    names: list[str] = []
    ordered_citations = sorted(
        citations,
        key=lambda citation: (citation.sort_order is None, citation.sort_order or 0, citation.material_name),
    )
    for citation in ordered_citations:
        material_name = citation.material_name.strip()
        if material_name and material_name not in names:
            names.append(material_name)
    return names


def _handout_topic_label(handout: HandoutContent) -> str:
    titles: list[str] = []
    for section in sorted(handout.sections, key=lambda item: item.sort_order):
        title = section.title.strip()
        if title and title not in titles:
            titles.append(title)
    return "、".join(titles[:3]) if titles else "当前任务"


def _lookup_citations(
    source_citation_ids: list[str],
    citations_by_id: dict[str, GeneratedContentCitationRead],
) -> list[GeneratedContentCitationRead]:
    return [citations_by_id[citation_id] for citation_id in source_citation_ids if citation_id in citations_by_id]


def _format_citation(citation: GeneratedContentCitationRead) -> str:
    base = f"{citation.material_name}, {_format_location(citation)}"
    snippet = _safe_citation_snippet(citation.hit_text)
    if snippet:
        return f"{base}: {snippet}"
    return base


def _safe_citation_snippet(hit_text: str | None) -> str:
    cleaned = _clean_text(hit_text or "")
    if not cleaned:
        return ""
    if any(marker in cleaned for marker in _UNSAFE_CITATION_SNIPPET_MARKERS):
        return ""
    return cleaned


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
