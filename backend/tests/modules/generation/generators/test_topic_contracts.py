import pytest
from pydantic import ValidationError

from app.modules.generation.generators.flashcard.schemas import FlashcardGenerationResult
from app.modules.generation.generators.knowledge_list.schemas import KnowledgeGenerationResult
from app.modules.generation.generators.mindmap.schemas import MindmapGenerationResult
from app.modules.generation.generators.outline.schemas import OutlineGenerationResult
from app.modules.generation.generators.quiz.schemas import QuizGenerationResult


def _payloads():
    return [
        (FlashcardGenerationResult, {"cards": [{"front": "什么是进程？", "back": "程序的一次执行过程", "tags": []}]}),
        (KnowledgeGenerationResult, {"items": [{"name": "进程", "definition": "程序的一次执行过程", "importance": "high", "related_section": "第一章 进程"}]}),
        (MindmapGenerationResult, {"root_node_id": "root", "nodes": [{"id": "root", "label": "进程", "summary": "操作系统概念", "level": 1}], "edges": []}),
        (OutlineGenerationResult, {"sections": [{"title": "进程概述", "summary": "理解进程", "review_suggestion": "对比程序与进程"}]}),
        (QuizGenerationResult, {"questions": [{"question_type": "single_choice", "question_text": "什么是进程？", "options": [{"id": key, "text": f"选项{key}", "explanation": f"解析{key}"} for key in "ABCD"], "correct_answer": "A", "explanation": "进程是程序的一次执行", "difficulty": "medium"}]}),
    ]


@pytest.mark.parametrize(("schema", "payload"), _payloads())
def test_generation_results_require_a_trimmed_topic_title(schema, payload) -> None:
    value = schema.model_validate({**payload, "topic_title": "  第一章 进程管理  "})
    assert value.topic_title == "第一章 进程管理"

    with pytest.raises(ValidationError):
        schema.model_validate(payload)
