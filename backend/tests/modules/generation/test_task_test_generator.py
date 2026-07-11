from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.task_test.generator import TaskTestGenerator
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.material_context.schemas import ContextChunk, MaterialContextResult


def _context() -> MaterialContextResult:
    return MaterialContextResult(
        no_parsed_material=False,
        chunks=[
            ContextChunk(
                material_id="mat_1",
                chunk_id="chunk_1",
                chunk_index=0,
                material_name="数据库讲义.pdf",
                page="2",
                page_index=1,
                heading="主键",
                content_text="主键用于唯一标识表中的一行。",
            )
        ],
    )


def test_task_test_generator_returns_questions_and_citations() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_1"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )

    output = TaskTestGenerator(model_provider=provider).generate(
        context=_context(),
        parameters={"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"},
    )

    assert output.title == "任务测试题"
    assert output.content_json is not None
    assert output.content_json["questions"][0]["correct_answer"] == "A"
    assert output.citation_chunk_ids == ["chunk_1"]


def test_task_test_generator_rejects_choice_question_without_options() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "single_choice",
                        "question_text": "主键的作用是什么？",
                        "options": [],
                        "correct_answer": "A",
                        "explanation": "主键用于唯一标识表中的一行。",
                        "source_citation_ids": ["chunk_1"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(context=_context(), parameters={"question_count": 1})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


@pytest.mark.parametrize(
    ("question_type", "correct_answer"),
    [
        ("single_choice", ""),
        ("single_choice", "   "),
        ("short_answer", ""),
        ("short_answer", "   "),
    ],
)
def test_task_test_generator_rejects_blank_string_correct_answer(
    question_type: str,
    correct_answer: str,
) -> None:
    question = {
        "id": "q_1",
        "question_type": question_type,
        "question_text": "What is a primary key?",
        "options": [{"id": "A", "text": "Uniquely identifies a row"}] if question_type == "single_choice" else [],
        "correct_answer": correct_answer,
        "explanation": "A primary key uniquely identifies one row.",
        "source_citation_ids": ["chunk_1"],
        "sort_order": 1,
    }
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "Answer these questions.",
                "questions": [question],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(context=_context(), parameters={"question_count": 1})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


@pytest.mark.parametrize(
    "correct_answer",
    [
        [],
        [""],
        ["   "],
        ["A", "   "],
    ],
)
def test_task_test_generator_rejects_invalid_multiple_choice_correct_answer_list(
    correct_answer: list[str],
) -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "Answer these questions.",
                "questions": [
                    {
                        "id": "q_1",
                        "question_type": "multiple_choice",
                        "question_text": "What is a primary key?",
                        "options": [{"id": "A", "text": "Uniquely identifies a row"}, {"id": "B", "text": "Stores images"}],
                        "correct_answer": correct_answer,
                        "explanation": "A primary key uniquely identifies one row.",
                        "source_citation_ids": ["chunk_1"],
                        "sort_order": 1,
                    }
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(context=_context(), parameters={"question_count": 1})

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
