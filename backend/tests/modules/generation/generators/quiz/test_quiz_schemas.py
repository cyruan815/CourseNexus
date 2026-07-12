from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.quiz.schemas import QuizCandidate, QuizParameters


def test_parameters_use_defaults_and_deduplicate_types() -> None:
    defaults = QuizParameters.model_validate({})
    assert defaults.question_count == 10
    assert defaults.question_types == ["single_choice", "true_false", "short_answer"]
    params = QuizParameters(question_types=["short_answer", "short_answer", "true_false"])
    assert params.question_types == ["short_answer", "true_false"]


@pytest.mark.parametrize("payload", [{"question_count": 0}, {"question_count": 51}, {"question_types": []}, {"unknown": 1}])
def test_parameters_reject_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        QuizParameters.model_validate(payload)


def _candidate(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "question_type": "single_choice",
        "question_text": "Which statement is correct?",
        "options": [
            {"id": "A", "text": "A1"}, {"id": "B", "text": "B1"},
            {"id": "C", "text": "C1"}, {"id": "D", "text": "D1"},
        ],
        "correct_answer": "A", "explanation": "Because A.", "difficulty": "medium",
        "source_chunk_ids": ["chunk-1"],
    }
    value.update(updates)
    return value


def test_single_choice_requires_four_options_and_one_option_id() -> None:
    assert QuizCandidate.model_validate(_candidate()).correct_answer == "A"
    with pytest.raises(ValidationError):
        QuizCandidate.model_validate(_candidate(correct_answer="E"))


def test_multiple_choice_requires_two_or_three_ordered_ids() -> None:
    value = _candidate(question_type="multiple_choice", correct_answer=["A", "C"])
    assert QuizCandidate.model_validate(value).correct_answer == ["A", "C"]
    with pytest.raises(ValidationError):
        QuizCandidate.model_validate(_candidate(question_type="multiple_choice", correct_answer=["C", "A"]))


def test_true_false_and_short_answer_have_no_options() -> None:
    true_false = _candidate(question_type="true_false", options=[], correct_answer=True)
    short_answer = _candidate(question_type="short_answer", options=[], correct_answer="Process")
    assert QuizCandidate.model_validate(true_false).correct_answer is True
    assert QuizCandidate.model_validate(short_answer).correct_answer == "Process"
