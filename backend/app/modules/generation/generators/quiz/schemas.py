from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Difficulty = Literal["easy", "medium", "hard"]
RequestedDifficulty = Literal["easy", "medium", "hard", "mixed"]


class QuizParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_count: int = Field(default=10, ge=1, le=50)
    question_types: list[Literal["single_choice"]] = Field(default_factory=lambda: ["single_choice"])
    difficulty: RequestedDifficulty = "mixed"
    focus: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("question_types")
    @classmethod
    def validate_question_types(cls, value: list[str]) -> list[str]:
        result = list(dict.fromkeys(value))
        if result != ["single_choice"]:
            raise ValueError("Quiz supports single-choice questions only")
        return result


class QuizOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Literal["A", "B", "C", "D"]
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Quiz option cannot be blank")
        return result


class QuizDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_type: Literal["single_choice"] = "single_choice"
    question_text: str = Field(min_length=1, max_length=1000)
    options: list[QuizOption]
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str = Field(min_length=1, max_length=2000)
    hint: str | None = Field(default=None, min_length=1, max_length=500)
    difficulty: Difficulty

    @field_validator("question_text", "explanation")
    @classmethod
    def trim_text(cls, value: str) -> str:
        result = value.strip()
        if not result:
            raise ValueError("Quiz text cannot be blank")
        return result

    @field_validator("hint")
    @classmethod
    def trim_hint(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_options(self) -> "QuizDraft":
        if [option.id for option in self.options] != ["A", "B", "C", "D"]:
            raise ValueError("Choice questions require options A-D")
        normalized = [" ".join(option.text.split()).casefold() for option in self.options]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Choice option text must be unique")
        return self


class QuizGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[QuizDraft] = Field(min_length=1)


class QuizQuestion(QuizDraft):
    id: str = Field(pattern=r"^q_\d{3}$")
    sort_order: int = Field(ge=1)


class QuizContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[QuizQuestion] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_order(self) -> "QuizContent":
        if [item.id for item in self.questions] != [f"q_{i:03d}" for i in range(1, len(self.questions) + 1)]:
            raise ValueError("Quiz IDs must be continuous")
        if [item.sort_order for item in self.questions] != list(range(1, len(self.questions) + 1)):
            raise ValueError("Quiz order must be continuous")
        normalized = [" ".join(item.question_text.split()).casefold() for item in self.questions]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Quiz questions must be unique")
        return self
