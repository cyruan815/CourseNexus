from __future__ import annotations

import pytest

from app.core.errors import CourseNexusError
from app.integrations.model_provider.mock import MockModelProvider
from app.modules.generation.generators.handout.generator import HandoutGenerator
from app.modules.generation.generators.handout.schemas import HandoutContent
from app.modules.material_context.schemas import ContextChunk, MaterialContextBatch, MaterialContextResult


def _context() -> MaterialContextResult:
    return MaterialContextResult(
        no_parsed_material=False,
        chunks=[
            ContextChunk(
                material_id="mat_1",
                chunk_id="chunk_1",
                chunk_index=0,
                material_name="数据库讲义.pdf",
                page="1",
                page_index=0,
                heading="关系模型",
                content_text="关系模型由关系、属性、元组和约束组成。",
            )
        ],
    )


def _batch() -> MaterialContextBatch:
    context = _context()
    return MaterialContextBatch(chunks=context.chunks, material_ids=["mat_1"], estimated_tokens=10)


def test_handout_generator_returns_structured_output_and_citations() -> None:
    provider = MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "学习关系模型的基本组成。",
                "learning_objectives": ["解释关系、属性和元组"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "关系模型",
                        "body": "关系模型用二维表组织数据。",
                        "key_points": ["关系对应表", "元组对应行"],
                        "source_citation_ids": ["chunk_1"],
                        "sort_order": 1,
                    }
                ],
                "summary": "本任务完成关系模型入门。",
            }
        }
    )

    output = HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={"language": "zh-CN", "detail_level": "standard"},
    )

    assert output.title == "今日讲义"
    assert output.content_json is not None
    assert output.content_json["overview"] == "学习关系模型的基本组成。"
    assert output.item_citation_chunk_ids == {"sec_1": ["chunk_1"]}


def test_handout_generator_rejects_schema_without_citation() -> None:
    provider = MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "概览",
                "learning_objectives": ["目标"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "无引用章节",
                        "body": "正文",
                        "key_points": ["重点"],
                        "source_citation_ids": [],
                        "sort_order": 1,
                    }
                ],
                "summary": "总结",
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        HandoutGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"

def test_handout_generator_rejects_known_physical_layer_term_misspelling() -> None:
    provider = MockModelProvider(
        structured_outputs={
            HandoutContent: {
                "overview": "Nyquest criterion is a physical layer formula.",
                "learning_objectives": ["Distinguish Nyquest and Shannon"],
                "sections": [
                    {
                        "id": "sec_1",
                        "title": "Nyquest and Shannon",
                        "body": "Nyquest should be spelled Nyquist in physical layer materials.",
                        "key_points": ["Nyquest is a misspelling"],
                        "source_citation_ids": ["chunk_1"],
                        "sort_order": 1,
                    }
                ],
                "summary": "Fix Nyquest before saving the handout.",
            }
        }
    )

    with pytest.raises(CourseNexusError) as exc_info:
        HandoutGenerator(model_provider=provider).generate(
            batches=(_batch(),),
            expected_material_ids=frozenset({"mat_1"}),
            parameters={},
        )

    assert exc_info.value.code == "GENERATION_SCHEMA_INVALID"
    assert exc_info.value.details == {"term": "Nyquest", "expected": "Nyquist"}
