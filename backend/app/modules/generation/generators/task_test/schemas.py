from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


QuestionType = Literal["single_choice", "multiple_choice", "true_false", "short_answer"]
_ALLOWED_QUESTION_TYPES = {"single_choice", "multiple_choice", "true_false", "short_answer"}


class QuestionTypeCount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_type: QuestionType
    question_count: int = Field(ge=1, le=20)


class TaskTestGenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(default=5, ge=1, le=20)
    question_types: list[QuestionType] = Field(default_factory=lambda: ["single_choice", "short_answer"])
    question_type_counts: list[QuestionTypeCount] | None = None
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
        cls._normalize_question_types_alias(normalized)
        raw_question_type_counts = normalized.get("question_type_counts")
        if isinstance(raw_question_type_counts, list) and raw_question_type_counts:
            normalized_items = cls._normalize_question_type_count_items(raw_question_type_counts)
            if normalized_items is not None:
                return cls._merge_count_normalization(normalized=normalized, normalized_counts=normalized_items)

        for key in ("items", "questions", "question_types"):
            raw_items = normalized.get(key)
            if not (
                isinstance(raw_items, list)
                and raw_items
                and all(isinstance(item, dict) for item in raw_items)
            ):
                continue
            normalized_items = cls._normalize_question_type_count_items(raw_items)
            if normalized_items is not None:
                return cls._merge_count_normalization(normalized=normalized, normalized_counts=normalized_items)

        label_map = cls._normalize_question_type_label_map(normalized)
        if label_map is not None:
            return cls._merge_count_normalization(normalized=normalized, normalized_counts=label_map)

        object_counts = cls._normalize_question_type_count_object(normalized)
        if object_counts is not None:
            return cls._merge_count_normalization(normalized=normalized, normalized_counts=object_counts)

        total_question_count = normalized.pop("total_question_count", None)
        if (
            "question_count" not in normalized
            and isinstance(total_question_count, int)
            and not isinstance(total_question_count, bool)
        ):
            normalized["question_count"] = total_question_count
        return normalized

    @model_validator(mode="after")
    def _sync_question_type_counts(self) -> "TaskTestGenerationParameters":
        if self.question_type_counts is None:
            return self
        if not self.question_type_counts:
            raise ValueError("question_type_counts must not be empty")
        question_count = sum(item.question_count for item in self.question_type_counts)
        question_types = list(dict.fromkeys(item.question_type for item in self.question_type_counts))
        if self.question_count != question_count:
            raise ValueError("question_count must equal the sum of question_type_counts")
        if self.question_types != question_types:
            raise ValueError("question_types must match question_type_counts order")
        return self

    @classmethod
    def _normalize_question_types_alias(cls, normalized: dict[str, object]) -> None:
        raw_types = normalized.pop("types", None)
        if raw_types is None:
            return
        if not isinstance(raw_types, list) or not raw_types or not all(isinstance(item, str) for item in raw_types):
            raise ValueError("types must be a non-empty question type list")
        question_types = [cls._normalize_question_type_value(item) for item in raw_types]
        if any(item is None for item in question_types):
            raise ValueError("types contains unsupported question type")
        question_types = list(dict.fromkeys(question_types))
        raw_question_types = normalized.get("question_types")
        if raw_question_types is not None and raw_question_types != question_types:
            raise ValueError("types conflicts with question_types")
        normalized["question_types"] = question_types
    @classmethod
    def _merge_count_normalization(
        cls,
        *,
        normalized: dict[str, object],
        normalized_counts: dict[str, object],
    ) -> dict[str, object]:
        total = normalized_counts["question_count"]
        question_types = normalized_counts["question_types"]
        question_type_counts = normalized_counts["question_type_counts"]

        for count_key in ("question_count", "total_question_count"):
            raw_count = normalized.get(count_key)
            if raw_count is None:
                continue
            if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count != total:
                raise ValueError(f"{count_key} conflicts with question_type_counts")

        raw_question_types = normalized.get("question_types")
        if isinstance(raw_question_types, list) and raw_question_types and all(
            isinstance(item, str) for item in raw_question_types
        ):
            normalized_question_types = [cls._normalize_question_type_value(item) for item in raw_question_types]
            if normalized_question_types != question_types:
                raise ValueError("question_types conflicts with question_type_counts")

        merged = {
            key: value
            for key, value in normalized.items()
            if key
            not in {
                "question_count",
                "total_question_count",
                "question_types",
                "question_type_counts",
                "items",
                "questions",
                "single_choice",
                "multiple_choice",
                "true_false",
                "short_answer",
            }
            and not (isinstance(key, str) and cls._extract_question_count_from_label(key) is not None)
        }
        if "difficulty" in normalized_counts and "difficulty" not in merged:
            merged["difficulty"] = normalized_counts["difficulty"]
        merged["question_count"] = total
        merged["question_types"] = question_types
        merged["question_type_counts"] = question_type_counts
        return merged

    @classmethod
    def _normalize_question_type_count_items(cls, items: list[object]) -> dict[str, object] | None:
        counts_by_type: dict[str, int] = {}
        question_types: list[str] = []
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
            counts_by_type[raw_type] = counts_by_type.get(raw_type, 0) + raw_count
            if raw_type not in question_types:
                question_types.append(raw_type)
            raw_difficulty = item.get("difficulty")
            if difficulty is None and raw_difficulty in {"easy", "medium", "hard"}:
                difficulty = str(raw_difficulty)
        return cls._count_payload(question_types=question_types, counts_by_type=counts_by_type, difficulty=difficulty)

    @classmethod
    def _normalize_question_type_count_object(cls, value: dict[str, object]) -> dict[str, object] | None:
        question_types: list[str] = []
        counts_by_type: dict[str, int] = {}
        for question_type in ("single_choice", "multiple_choice", "true_false", "short_answer"):
            raw_count = value.get(question_type)
            if raw_count is None:
                continue
            if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count <= 0:
                return None
            counts_by_type[question_type] = counts_by_type.get(question_type, 0) + raw_count
            question_types.append(question_type)
        return cls._count_payload(question_types=question_types, counts_by_type=counts_by_type)

    @classmethod
    def _normalize_question_type_label_map(cls, value: dict[str, object]) -> dict[str, object] | None:
        count_labels = [key for key in value if isinstance(key, str) and cls._extract_question_count_from_label(key) is not None]
        if not count_labels:
            return None
        question_types: list[str] = []
        counts_by_type: dict[str, int] = {}
        difficulty_value = value.get("difficulty")
        difficulty = difficulty_value if isinstance(difficulty_value, str) and difficulty_value in {"easy", "medium", "hard"} else None
        for label in count_labels:
            count = cls._extract_question_count_from_label(label)
            if count is None:
                return None
            raw_value = value.get(label)
            item_difficulty: str | None = None
            if isinstance(raw_value, dict):
                question_type = cls._normalize_question_type_value(raw_value.get("question_type") or raw_value.get("type"))
                raw_count = raw_value.get("question_count") if "question_count" in raw_value else raw_value.get("count")
                if question_type is None:
                    return None
                if raw_count is not None:
                    if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count <= 0:
                        return None
                    if raw_count != count:
                        raise ValueError(f"{label} conflicts with question_count")
                raw_difficulty = raw_value.get("difficulty")
                if isinstance(raw_difficulty, str) and raw_difficulty in {"easy", "medium", "hard"}:
                    item_difficulty = raw_difficulty
            else:
                question_type = cls._normalize_question_type_value(raw_value)
                if question_type is None:
                    return None
            if difficulty is None and item_difficulty is not None:
                difficulty = item_difficulty
            counts_by_type[question_type] = counts_by_type.get(question_type, 0) + count
            if question_type not in question_types:
                question_types.append(question_type)
        return cls._count_payload(question_types=question_types, counts_by_type=counts_by_type, difficulty=difficulty)

    @staticmethod
    def _count_payload(
        *,
        question_types: list[str],
        counts_by_type: dict[str, int],
        difficulty: str | None = None,
    ) -> dict[str, object] | None:
        question_count = sum(counts_by_type.values())
        if question_count <= 0:
            return None
        normalized: dict[str, object] = {
            "question_count": question_count,
            "question_types": question_types,
            "question_type_counts": [
                {"question_type": question_type, "question_count": counts_by_type[question_type]}
                for question_type in question_types
            ],
        }
        if difficulty is not None:
            normalized["difficulty"] = difficulty
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
            "单选题": "single_choice",
            "选择题": "single_choice",
            "multiple": "multiple_choice",
            "multiplechoice": "multiple_choice",
            "多选题": "multiple_choice",
            "truefalse": "true_false",
            "判断题": "true_false",
            "shortanswer": "short_answer",
            "short": "short_answer",
            "简答题": "short_answer",
            "问答题": "short_answer",
            "计算题": "short_answer",
            "证明题": "short_answer",
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
