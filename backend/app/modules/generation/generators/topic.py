from __future__ import annotations

import re
from typing import Annotated

from pydantic import StringConstraints

from app.core.errors import CourseNexusError


TopicTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]

_CHINESE_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


def contains_chinese(text: str) -> bool:
    return _CHINESE_CHARACTER.search(text) is not None


def ensure_chinese_topic(topic_title: str) -> str:
    result = topic_title.strip()
    if not contains_chinese(result):
        raise CourseNexusError(
            code="GENERATION_SCHEMA_INVALID",
            message="Generated topic title must be Chinese",
        )
    return result
