from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.modules.generation.generators.quiz.generator import QuizGenerator
from app.modules.generation.generators.quiz.schemas import QuizGenerationResult
from app.modules.material_context.schemas import MaterialGenerationContext
from tests.modules.generation.conftest import RecordingStructuredModelProvider


def _context() -> MaterialGenerationContext:
    return MaterialGenerationContext(chunks=[], material_ids=["m1", "m2"], text="ALL MATERIALS", estimated_tokens=10)


def _question(text: str) -> dict[str, object]:
    return {
        "question_type": "single_choice",
        "question_text": text,
        "options": [
            {"id": "A", "text": "选项A", "explanation": "解析A"}, {"id": "B", "text": "选项B", "explanation": "解析B"},
            {"id": "C", "text": "选项C", "explanation": "解析C"}, {"id": "D", "text": "选项D", "explanation": "解析D"},
        ],
        "correct_answer": "A",
        "explanation": "因为A符合定义",
        "difficulty": "medium",
    }


def test_quiz_uses_one_final_model_result_and_assigns_ids() -> None:
    provider = RecordingStructuredModelProvider({"topic_title": "第一章 进程管理", "questions": [_question("问题一"), _question("问题二")]})
    output = QuizGenerator(model_provider=provider).generate(
        context=_context(), parameters={"question_count": 2}
    )
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is QuizGenerationResult
    assert "ALL MATERIALS" in provider.calls[0][0]
    assert [item["id"] for item in output.content_json["questions"]] == ["q_001", "q_002"]
    assert "source_citation_ids" not in output.content_json["questions"][0]
    assert output.content_json["questions"][0]["options"][1]["explanation"] == "解析B"
    assert output.title == "第一章 进程管理"
    assert "plausible distractors" in provider.calls[0][0]
    assert "conceptual understanding" in provider.calls[0][0]
    assert "do not reveal the correct answer" in provider.calls[0][0]
    assert "Simplified Chinese topic_title" in provider.calls[0][0]


def test_quiz_retries_once_when_the_first_result_contains_an_english_question() -> None:
    provider = RecordingStructuredModelProvider(
        {"topic_title": "第一章 进程管理", "questions": [_question("Which statement describes a process?")]},
        {"topic_title": "第一章 进程管理", "questions": [_question("下列哪项描述了进程？")]},
    )

    output = QuizGenerator(model_provider=provider).generate(context=_context(), parameters={"question_count": 1})

    assert len(provider.calls) == 2
    assert "Regenerate the entire quiz" in provider.calls[1][0]
    assert output.content_json["questions"][0]["question_text"] == "下列哪项描述了进程？"


def test_quiz_rejects_results_that_remain_english_after_one_retry() -> None:
    provider = RecordingStructuredModelProvider(
        {"topic_title": "第一章 进程管理", "questions": [_question("What is a process?")]},
        {"topic_title": "Process Management", "questions": [_question("Which option is correct?")]},
    )

    with pytest.raises(CourseNexusError) as exc_info:
        QuizGenerator(model_provider=provider).generate(context=_context(), parameters={"question_count": 1})

    assert len(provider.calls) == 2
    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
