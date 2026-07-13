from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["single_choice", "multiple_choice", "true_false", "short_answer"]
_ALLOWED_QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "short_answer"}


class TaskTestGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=5, ge=1, le=20)
    question_types: list[QuestionType] = Field(default_factory=lambda: ["single_choice", "short_answer"])
    difficulty: Literal["easy", "medium", "hard"] = "medium"

    @model_validator(mode="before")
    @classmethod
    def _normalize_question_type_counts(cls, value: object) -> object:
        if isinstance(value, list):
            normalized_items = cls._normalize_question_type_count_items(value)
            return normalized_items if normalized_items is not None else value
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        raw_question_types = next(
            (
                normalized.get(key)
                for key in ("question_types", "items", "question_type_counts")
                if isinstance(normalized.get(key), list)
            ),
            None,
        )
        if (
            isinstance(raw_question_types, list)
            and raw_question_types
            and all(isinstance(item, dict) for item in raw_question_types)
        ):
            normalized_items = cls._normalize_question_type_count_items(raw_question_types)
            if normalized_items is not None:
                raw_difficulty = normalized.get("difficulty")
                if raw_difficulty in {"easy", "medium", "hard"} and "difficulty" not in normalized_items:
                    normalized_items["difficulty"] = raw_difficulty
                return normalized_items
        total_question_count = normalized.pop("total_question_count", None)
        if (
            "question_count" not in normalized
            and isinstance(total_question_count, int)
            and not isinstance(total_question_count, bool)
        ):
            normalized["question_count"] = total_question_count
        label_map = cls._normalize_question_type_label_map(normalized)
        if label_map is not None:
            return label_map
        question_types: list[str] = []
        question_count = 0
        for question_type in ("single_choice", "multiple_choice", "true_false", "short_answer"):
            raw_count = normalized.pop(question_type, None)
            if raw_count is None:
                continue
            if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count <= 0:
                normalized[question_type] = raw_count
                continue
            question_count += raw_count
            question_types.append(question_type)
        if question_count:
            normalized["question_count"] = question_count
            normalized.setdefault("question_types", question_types)
        return normalized

    @classmethod
    def _normalize_question_type_count_items(cls, items: list[object]) -> dict[str, object] | None:
        question_types: list[str] = []
        question_count = 0
        difficulty: str | None = None
        for item in items:
            if not isinstance(item, dict):
                return None
            raw_type = cls._normalize_question_type_value(item.get("question_type") or item.get("type"))
            raw_count = item.get("question_count") if "question_count" in item else item.get("count")
            if raw_type is None:
                return None
            if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count <= 0:
                return None
            question_count += raw_count
            if raw_type not in question_types:
                question_types.append(raw_type)
            raw_difficulty = item.get("difficulty")
            if difficulty is None and raw_difficulty in {"easy", "medium", "hard"}:
                difficulty = str(raw_difficulty)
        if question_count <= 0:
            return None
        normalized: dict[str, object] = {"question_count": question_count, "question_types": question_types}
        if difficulty is not None:
            normalized["difficulty"] = difficulty
        return normalized

    @classmethod
    def _normalize_question_type_label_map(cls, value: dict[str, object]) -> dict[str, object] | None:
        if not value:
            return None
        if any(key in {"question_count", "question_types", "difficulty"} for key in value):
            return None
        question_types: list[str] = []
        question_count = 0
        difficulty_value = value.get("difficulty")
        for label, raw_question_type in value.items():
            if not isinstance(label, str):
                return None
            question_type = cls._normalize_question_type_value(raw_question_type)
            if question_type is None:
                return None
            count = cls._extract_question_count_from_label(label)
            if count is None:
                return None
            question_count += count
            if question_type not in question_types:
                question_types.append(question_type)
        if question_count <= 0:
            return None
        normalized: dict[str, object] = {"question_count": question_count, "question_types": question_types}
        if isinstance(difficulty_value, str) and difficulty_value in {"easy", "medium", "hard"}:
            normalized["difficulty"] = difficulty_value
        return normalized

    @staticmethod
    def _extract_question_count_from_label(label: str) -> int | None:
        match = re.search(r"([一二两三四五六七八九十\d]+)", label)
        if not match:
            return None
        raw_value = match.group(1)
        if raw_value.isdigit():
            return int(raw_value)
        digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if raw_value in digits:
            return digits[raw_value]
        if raw_value == "十":
            return 10
        if "十" in raw_value:
            tens_raw, ones_raw = raw_value.split("十", 1)
            tens = 1 if tens_raw == "" else digits.get(tens_raw)
            ones = 0 if ones_raw == "" else digits.get(ones_raw)
            if tens is None or ones is None:
                return None
            return tens * 10 + ones
        return None

    @classmethod
    def _normalize_question_type_value(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "single": "single_choice",
            "singlechoice": "single_choice",
            "multiple": "multiple_choice",
            "multiplechoice": "multiple_choice",
            "truefalse": "true_false",
            "shortanswer": "short_answer",
            "short": "short_answer",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in _ALLOWED_QUESTION_TYPES:
            return normalized
        return None

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
        if self.question_type == "single_choice" and not (
            isinstance(self.correct_answer, str) and self.correct_answer.strip()
        ):
            raise ValueError("single_choice correct_answer must be a string")
        if self.question_type == "multiple_choice" and not (
            isinstance(self.correct_answer, list)
            and self.correct_answer
            and all(isinstance(item, str) and item.strip() for item in self.correct_answer)
        ):
            raise ValueError("multiple_choice correct_answer must be a non-empty string list")
        if self.question_type == "true_false" and not isinstance(self.correct_answer, bool):
            raise ValueError("true_false correct_answer must be boolean")
        if self.question_type == "short_answer" and not (
            isinstance(self.correct_answer, str) and self.correct_answer.strip()
        ):
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
