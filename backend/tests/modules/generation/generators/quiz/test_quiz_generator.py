from __future__ import annotations

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
            {"id": "A", "text": "A"}, {"id": "B", "text": "B"},
            {"id": "C", "text": "C"}, {"id": "D", "text": "D"},
        ],
        "correct_answer": "A",
        "explanation": "Because A",
        "difficulty": "medium",
    }


def test_quiz_uses_one_final_model_result_and_assigns_ids() -> None:
    provider = RecordingStructuredModelProvider({"questions": [_question("Q1"), _question("Q2")]})
    output = QuizGenerator(model_provider=provider).generate(
        context=_context(), parameters={"question_count": 2}
    )
    assert len(provider.calls) == 1
    assert provider.calls[0][1] is QuizGenerationResult
    assert "ALL MATERIALS" in provider.calls[0][0]
    assert [item["id"] for item in output.content_json["questions"]] == ["q_001", "q_002"]
    assert "source_citation_ids" not in output.content_json["questions"][0]
