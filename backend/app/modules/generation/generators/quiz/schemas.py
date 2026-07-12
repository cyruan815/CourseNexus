from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["single_choice"]
Difficulty = Literal["easy", "medium", "hard"]
RequestedDifficulty = Literal["easy", "medium", "hard", "mixed"]


class QuizParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=10, ge=1, le=50)
    question_types: list[QuestionType] = Field(
        default_factory=lambda: ["single_choice"]
    )
    difficulty: RequestedDifficulty = "mixed"
    focus: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("question_types")
    @classmethod
    def deduplicate_question_types(cls, value: list[QuestionType]) -> list[QuestionType]:
        result = list(dict.fromkeys(value))
        if not result:
            raise ValueError("At least one question type is required")
        return result


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal["A", "B", "C", "D"]
    text: str = Field(min_length=1, max_length=500)


class _QuestionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_type: QuestionType
    question_text: str = Field(min_length=1, max_length=1000)
    options: list[QuizOption] = Field(default_factory=list)
    correct_answer: str | list[str] | bool
    explanation: str = Field(min_length=1, max_length=2000)
    difficulty: Difficulty

    @model_validator(mode="after")
    def validate_question_shape(self) -> "_QuestionBase":
        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Quiz option IDs must be unique")
        if self.question_type == "single_choice":
            if option_ids != ["A", "B", "C", "D"]:
                raise ValueError("Choice questions require options A-D")
        elif self.options:
            raise ValueError("Non-choice questions cannot have options")

        answer = self.correct_answer
        if self.question_type == "single_choice":
            if isinstance(answer, bool) or not isinstance(answer, str) or answer not in option_ids:
                raise ValueError("Single choice answer must be one option ID")
        return self


class QuizCandidate(_QuestionBase):
    source_chunk_ids: list[str] = Field(min_length=1)


class QuizMapResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[QuizCandidate] = Field(default_factory=list)
    citation_chunk_ids: list[str] = Field(default_factory=list)


class QuizQuestion(_QuestionBase):
    id: str = Field(pattern=r"^q_\d{3}$")
    source_citation_ids: list[str] = Field(default_factory=list)
    sort_order: int = Field(ge=1)


class QuizContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[QuizQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_order(self) -> "QuizContent":
        expected_ids = [f"q_{index:03d}" for index in range(1, len(self.questions) + 1)]
        if [question.id for question in self.questions] != expected_ids:
            raise ValueError("Quiz question IDs must be continuous")
        if [question.sort_order for question in self.questions] != list(range(1, len(self.questions) + 1)):
            raise ValueError("Quiz sort order must be continuous")
        normalized = [" ".join(question.question_text.split()).casefold() for question in self.questions]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Quiz questions must be unique")
        return self
