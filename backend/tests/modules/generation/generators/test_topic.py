import pytest
from pydantic import TypeAdapter

from app.core.errors import CourseNexusError
from app.modules.generation.generators.topic import TopicTitle, contains_chinese, ensure_chinese_topic


def test_topic_title_is_trimmed_and_length_limited() -> None:
    adapter = TypeAdapter(TopicTitle)

    assert adapter.validate_python("  第七章 物理层  ") == "第七章 物理层"
    with pytest.raises(ValueError):
        adapter.validate_python("主题" * 31)


def test_chinese_topic_check_allows_professional_abbreviations() -> None:
    assert contains_chinese("TCP 与 IP 协议") is True
    assert contains_chinese("Physical Layer") is False
    assert ensure_chinese_topic("OSI 模型") == "OSI 模型"


def test_non_chinese_topic_raises_generation_schema_error() -> None:
    with pytest.raises(CourseNexusError) as exc_info:
        ensure_chinese_topic("Physical Layer")

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
