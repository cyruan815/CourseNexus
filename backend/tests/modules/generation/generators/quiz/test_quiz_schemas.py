from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.generation.generators.quiz.schemas import QuizCandidate, QuizParameters


def test_parameters_use_defaults_and_deduplicate_types() -> None:
    defaults = QuizParameters.model_validate({})
    assert defaults.question_count == 10
    assert defaults.question_types == ["single_choice"]
    params = QuizParameters(question_types=["single_choice", "single_choice"])
    assert params.question_types == ["single_choice"]


@pytest.mark.parametrize(
    "payload",
    [
        {"question_count": 0},
        {"question_count": 51},
        {"question_types": []},
        {"question_types": ["multiple_choice"]},
        {"question_types": ["true_false"]},
        {"question_types": ["short_answer"]},
        {"unknown": 1},
    ],
)
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
