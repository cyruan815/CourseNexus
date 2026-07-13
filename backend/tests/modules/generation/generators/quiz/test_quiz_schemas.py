import pytest
from pydantic import ValidationError

from app.modules.generation.generators.quiz.schemas import QuizDraft, QuizParameters


def _question(**updates):
    value = {
        "question_type": "single_choice", "question_text": "Question?",
        "options": [{"id": key, "text": key} for key in "ABCD"],
        "correct_answer": "A", "explanation": "Explanation", "difficulty": "medium",
    }
    value.update(updates)
    return value


def test_quiz_defaults_to_ten_single_choice_questions() -> None:
    params = QuizParameters()
    assert params.question_count == 10
    assert params.question_types == ["single_choice"]


@pytest.mark.parametrize("value", ["", "   "])
def test_quiz_rejects_blank_question_and_explanation(value: str) -> None:
    with pytest.raises(ValidationError):
        QuizDraft.model_validate(_question(question_text=value))
    with pytest.raises(ValidationError):
        QuizDraft.model_validate(_question(explanation=value))


def test_quiz_requires_exactly_four_ordered_options() -> None:
    assert QuizDraft.model_validate(_question()).correct_answer == "A"
    with pytest.raises(ValidationError):
        QuizDraft.model_validate(_question(options=[{"id": "A", "text": "A"}]))
