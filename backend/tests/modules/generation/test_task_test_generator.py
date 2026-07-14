from __future__ import annotations

import pytest

from pydantic import ValidationError

from app.core.errors import CourseNexusError
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.task_test.generator import TaskTestGenerator
from app.modules.generation.generators.task_test.schemas import TaskTestContent, TaskTestGenerationParameters
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


def _choice_options(*, ids: tuple[str, str, str, str] = ("A", "B", "C", "D")) -> list[dict[str, str]]:
    texts = ("唯一标识一行", "存储图片", "表达外键", "删除数据")
    return [{"id": option_id, "text": text} for option_id, text in zip(ids, texts, strict=True)]


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
        "options": options if options is not None else _choice_options(),
        "correct_answer": correct_answer,
        "explanation": "主键用于唯一标识表中的一行。",
        "source_citation_ids": ["chunk_1"],
        "sort_order": sort_order,
    }


class RecordingTaskTestModelProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def answer_question(self, *, question, context_chunks):  # pragma: no cover - unused in generator tests
        raise AssertionError("answer_question should not be called")

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        assert output_schema is TaskTestContent
        return TaskTestContent.model_validate(
            {
                "instructions": "完成下列题目。",
                "questions": [_question_payload("q_1")],
            }
        )


_EXPECTED_TYPE_COUNTS = [
    {"question_type": "single_choice", "question_count": 10},
    {"question_type": "short_answer", "question_count": 3},
]


@pytest.mark.parametrize(
    "raw_parameters",
    [
        {"single_choice": 10, "short_answer": 3},
        [{"type": "single_choice", "count": 10}, {"type": "short_answer", "count": 3}],
        {"items": [{"question_type": "single_choice", "question_count": 10}, {"question_type": "short_answer", "question_count": 3}]},
        {"question_types": [{"type": "single_choice", "count": 10}, {"type": "short_answer", "count": 3}]},
        {"question_type_counts": [{"question_type": "single_choice", "question_count": 10}, {"question_type": "short_answer", "question_count": 3}]},
        {"10道选择题": "single_choice", "3道计算题": "short_answer"},
    ],
)
def test_task_test_generation_parameters_normalizes_question_type_counts_variants(raw_parameters: object) -> None:
    params = TaskTestGenerationParameters.model_validate(raw_parameters)

    assert params.question_count == 13
    assert params.question_types == ["single_choice", "short_answer"]
    assert params.model_dump(mode="json")["question_type_counts"] == _EXPECTED_TYPE_COUNTS


def test_task_test_generation_parameters_accepts_types_alias_for_question_types() -> None:
    params = TaskTestGenerationParameters.model_validate(
        {"question_count": 7, "types": ["single_choice", "short_answer"]}
    )

    assert params.question_count == 7
    assert params.question_types == ["single_choice", "short_answer"]
    assert params.question_type_counts is None

@pytest.mark.parametrize(
    "raw_parameters",
    [
        {"question_count": 12, "question_type_counts": [{"question_type": "single_choice", "question_count": 10}, {"question_type": "short_answer", "question_count": 3}]},
        {"question_types": ["short_answer", "single_choice"], "question_type_counts": [{"question_type": "single_choice", "question_count": 10}, {"question_type": "short_answer", "question_count": 3}]},
    ],
)
def test_task_test_generation_parameters_rejects_conflicting_question_type_counts(raw_parameters: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TaskTestGenerationParameters.model_validate(raw_parameters)

def test_task_test_generator_returns_questions_and_citations() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [_question_payload("q_1")],
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
    assert [option["id"] for option in output.content_json["questions"][0]["options"]] == ["A", "B", "C", "D"]
    assert output.content_json["questions"][0]["correct_answer"] == "A"
    assert output.item_citation_chunk_ids == {"q_1": ["chunk_1"]}


def test_task_test_generator_prompt_requires_four_letter_choice_options() -> None:
    provider = RecordingTaskTestModelProvider()

    TaskTestGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"question_count": 1, "question_types": ["single_choice"], "difficulty": "medium"},
    )

    assert "单选和多选题必须恰好 4 个选项" in provider.prompts[0]
    assert "A、B、C、D" in provider.prompts[0]


def test_task_test_generator_normalizes_choice_option_ids_per_question_order() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload(
                        "q_1",
                        options=_choice_options(ids=("opt_1", "opt_2", "opt_3", "opt_4")),
                        correct_answer="opt_2",
                        sort_order=1,
                    ),
                    _question_payload(
                        "q_2",
                        question_text="外键的作用是什么？",
                        options=_choice_options(ids=("opt_5", "opt_6", "opt_7", "opt_8")),
                        correct_answer="opt_6",
                        sort_order=2,
                    ),
                ],
            }
        }
    )

    output = TaskTestGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"question_count": 2, "question_types": ["single_choice"], "difficulty": "medium"},
    )

    questions = output.content_json["questions"]
    assert [[option["id"] for option in question["options"]] for question in questions] == [
        ["A", "B", "C", "D"],
        ["A", "B", "C", "D"],
    ]
    assert [question["correct_answer"] for question in questions] == ["B", "B"]


def test_task_test_generator_normalizes_multiple_choice_answers_per_question_order() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload(
                        "q_1",
                        question_type="multiple_choice",
                        options=_choice_options(ids=("opt_5", "opt_6", "opt_7", "opt_8")),
                        correct_answer=["opt_5", "opt_7"],
                    )
                ],
            }
        }
    )

    output = TaskTestGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"question_count": 1, "question_types": ["multiple_choice"], "difficulty": "medium"},
    )

    question = output.content_json["questions"][0]
    assert [option["id"] for option in question["options"]] == ["A", "B", "C", "D"]
    assert question["correct_answer"] == ["A", "C"]


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
        _question_payload("q_1", correct_answer="Z"),
        _question_payload("q_1", question_type="multiple_choice", correct_answer=["A", "Z"]),
        _question_payload("q_1", question_type="multiple_choice", correct_answer=["A", "A"]),
        _question_payload(
            "q_1",
            options=[
                {"id": "A", "text": "唯一标识一行"},
                {"id": "A", "text": "重复选项"},
                {"id": "C", "text": "表达外键"},
                {"id": "D", "text": "删除数据"},
            ],
        ),
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


def test_task_test_generator_rejects_choice_question_with_non_four_options() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload(
                        "q_1",
                        options=[
                            {"id": "A", "text": "唯一标识一行"},
                            {"id": "B", "text": "存储图片"},
                            {"id": "C", "text": "表达外键"},
                        ],
                    )
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
        "options": _choice_options() if question_type == "single_choice" else [],
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
                        "options": _choice_options(),
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


def test_task_test_generator_prompt_includes_question_type_count_requirements() -> None:
    provider = RecordingTaskTestModelProvider()

    TaskTestGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={
            "question_type_counts": [{"question_type": "single_choice", "question_count": 1}],
            "difficulty": "medium",
        },
    )

    assert "每种题型数量" in provider.prompts[0]
    assert "single_choice 1 道" in provider.prompts[0]


def test_task_test_generator_rejects_question_type_count_mismatch() -> None:
    provider = MockModelProvider(
        structured_outputs={
            TaskTestContent: {
                "instructions": "完成下列题目。",
                "questions": [
                    _question_payload("q_1", sort_order=1),
                    _question_payload(
                        "q_2",
                        question_type="short_answer",
                        question_text="说明主键为什么必须唯一。",
                        options=[],
                        correct_answer="主键必须唯一标识一行。",
                        sort_order=2,
                    ),
                    _question_payload(
                        "q_3",
                        question_type="short_answer",
                        question_text="说明外键的作用。",
                        options=[],
                        correct_answer="外键用于表达表之间的关系。",
                        sort_order=3,
                    ),
                ],
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        TaskTestGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={
                "question_type_counts": [
                    {"question_type": "single_choice", "question_count": 2},
                    {"question_type": "short_answer", "question_count": 1},
                ]
            },
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
