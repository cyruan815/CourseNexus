from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["single_choice", "multiple_choice", "true_false", "short_answer"]


class TaskTestGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=5, ge=1, le=20)
    question_types: list[QuestionType] = Field(default_factory=lambda: ["single_choice", "short_answer"])
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @field_validator("question_types")
    @classmethod
    def _question_types_non_empty(cls, value: list[QuestionType]) -> list[QuestionType]:
        if not value:
            raise ValueError("question_types must not be empty")
        return list(dict.fromkeys(value))


class TaskTestOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class TaskTestQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question_type: QuestionType
    question_text: str = Field(min_length=1)
    options: list[TaskTestOption] = Field(default_factory=list)
    correct_answer: str | bool | list[str]
    explanation: str = Field(min_length=1)
    source_citation_ids: list[str] = Field(min_length=1)
    sort_order: int = Field(ge=1)

    @model_validator(mode="after")
    def _validate_by_type(self) -> "TaskTestQuestion":
        if self.question_type in {"single_choice", "multiple_choice"} and not self.options:
            raise ValueError("choice questions require options")
        if self.question_type == "single_choice" and not isinstance(self.correct_answer, str):
            raise ValueError("single_choice correct_answer must be a string")
        if self.question_type == "multiple_choice" and not (
            isinstance(self.correct_answer, list) and all(isinstance(item, str) and item for item in self.correct_answer)
        ):
            raise ValueError("multiple_choice correct_answer must be a non-empty string list")
        if self.question_type == "true_false" and not isinstance(self.correct_answer, bool):
            raise ValueError("true_false correct_answer must be boolean")
        if self.question_type == "short_answer" and not isinstance(self.correct_answer, str):
            raise ValueError("short_answer correct_answer must be a string")
        return self

    @field_validator("source_citation_ids")
    @classmethod
    def _citations_non_empty(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("source_citation_ids must contain non-empty strings")
        return value


class TaskTestContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instructions: str = Field(min_length=1)
    questions: list[TaskTestQuestion] = Field(min_length=1)
