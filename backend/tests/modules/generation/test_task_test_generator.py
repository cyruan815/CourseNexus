from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.task_test.generator import TaskTestGenerator
from app.modules.generation.generators.task_test.schemas import TaskTestContent
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch, MaterialContextResult


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


def _batch() -> MaterialContextBatch:
    context = _context()
    return MaterialContextBatch(chunks=context.chunks, material_ids=["mat_1"], estimated_tokens=10)


def _question_payload(
    question_id: str,
    *,
    question_type: str = "single_choice",
    question_text: str = "主键的作用是什么？",
    options: list[dict[str, str]] | None = None,
    correct_answer: object = "A",
    sort_order: int = 1,
) -> dict[str, object]:
    return {
        "id": question_id,
        "question_type": question_type,
        "question_text": question_text,
        "options": options if options is not None else [{"id": "A", "text": "唯一标识一行"}, {"id": "B", "text": "存储图片"}],
        "correct_answer": correct_answer,
        "explanation": "主键用于唯一标识表中的一行。",
        "source_citation_ids": ["chunk_1"],
        "sort_order": sort_order,
    }


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
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"},
    )

    assert output.title == "任务测试题"
    assert output.content_json is not None
    assert output.content_json["questions"][0]["correct_answer"] == "A"
    assert output.item_citation_chunk_ids == {"q_1": ["chunk_1"]}


def test_task_test_generator_rejects_question_count_mismatch() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload("q_1", sort_order=1),
                    _question_payload("q_2", question_text="主键能否为空？", correct_answer="B", sort_order=2),
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1, "question_types": ["single_choice"]},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_task_test_generator_rejects_question_type_outside_requested_whitelist() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload(
                        "q_1",
                        question_type="short_answer",
                        options=[],
                        correct_answer="主键用于唯一标识一行。",
                    ),
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1, "question_types": ["single_choice"]},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


@pytest.mark.parametrize(
    "questions",
    [
        [_question_payload("q_1", sort_order=1), _question_payload("q_1", question_text="主键能否为空？", sort_order=2)],
        [_question_payload("q_1", sort_order=1), _question_payload("q_2", question_text="主键能否为空？", sort_order=1)],
        [_question_payload("q_1", sort_order=1), _question_payload("q_2", question_text="主键能否为空？", sort_order=3)],
        [_question_payload("q_1", sort_order=1), _question_payload("q_3", question_text="主键能否为空？", sort_order=2)],
    ],
)
def test_task_test_generator_rejects_duplicate_or_non_contiguous_question_identity(questions: list[dict[str, object]]) -> None:
    provider = MockModelProvider(structured_outputs={TaskTestContent: {"instructions": "完成下列题目。", "questions": questions}})

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 2, "question_types": ["single_choice"]},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


@pytest.mark.parametrize(
    "question",
    [
        _question_payload("q_1", correct_answer="C"),
        _question_payload("q_1", question_type="multiple_choice", correct_answer=["A", "C"]),
        _question_payload("q_1", question_type="multiple_choice", correct_answer=["A", "A"]),
        _question_payload("q_1", options=[{"id": "A", "text": "唯一标识一行"}, {"id": "A", "text": "重复选项"}]),
    ],
)
def test_task_test_generator_rejects_invalid_choice_option_contract(question: dict[str, object]) -> None:
    provider = MockModelProvider(structured_outputs={TaskTestContent: {"instructions": "完成下列题目。", "questions": [question]}})

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1, "question_types": ["single_choice", "multiple_choice"]},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


def test_task_test_generator_rejects_duplicate_question_texts() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload("q_1", sort_order=1),
                    _question_payload("q_2", sort_order=2),
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 2, "question_types": ["single_choice"]},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"


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
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1},
        )

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
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1},
        )

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
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={"question_count": 1},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
