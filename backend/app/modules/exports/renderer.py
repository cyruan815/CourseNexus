from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.modules.generated_content.schemas import GeneratedContentCitationRead, GeneratedContentRead
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestQuestion


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


def _validate_task_test_content(content_json: dict[str, Any] | list[Any] | None) -> TaskTestContent:
    if not isinstance(content_json, dict):
        raise _invalid_content_error()
    try:
        return TaskTestContent.model_validate(content_json)
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
    citations = [citations_by_id[citation_id] for citation_id in source_citation_ids if citation_id in citations_by_id]
    if not citations:
        return ["Sources: unavailable"]

    lines = ["Sources:"]
    for citation in citations:
        lines.append(f"- {citation.material_name}, {_format_location(citation)}: {citation.hit_text}")
    return lines


def _format_location(citation: GeneratedContentCitationRead) -> str:
    if citation.page:
        return f"p.{citation.page}"
    if citation.page_index is not None:
        return f"p.{citation.page_index}"
    return "p.unknown"


def _invalid_content_error() -> CourseNexusError:
    return CourseNexusError(
        code="EXPORT_CONTENT_INVALID",
        message="生成内容结构不支持导出",
        status_code=500,
    )
