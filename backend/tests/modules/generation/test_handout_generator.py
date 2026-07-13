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


class PromptCapturingModelProvider(MockModelProvider):
    def __init__(self, structured_outputs: dict[type[HandoutContent], dict]) -> None:
        super().__init__(structured_outputs=structured_outputs)
        self.prompts: list[str] = []

    def generate_structured(self, *, prompt, output_schema):
        self.prompts.append(prompt)
        return super().generate_structured(prompt=prompt, output_schema=output_schema)


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


def test_handout_generator_prompt_includes_task_context_and_quality_requirements() -> None:
    provider = PromptCapturingModelProvider(
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

    HandoutGenerator(model_provider=provider).generate(
        batches=(_batch(),),
        expected_material_ids=frozenset({"mat_1"}),
        parameters={
            "language": "zh-CN",
            "detail_level": "standard",
            "subtask_title": "物理层概念与通信基础",
            "subtask_description": "理解物理层基本概念和通信模型。",
            "plan_goal": "两天内深度学习计算机网络物理层。",
            "diagnostic_weak_area": "calculation",
            "diagnostic_explanation_style": "step_by_step",
        },
    )

    prompt = provider.prompts[0]
    assert "当前二级任务标题：物理层概念与通信基础" in prompt
    assert "当前二级任务描述：理解物理层基本概念和通信模型。" in prompt
    assert "学习计划目标：两天内深度学习计算机网络物理层。" in prompt
    assert "诊断薄弱方向：calculation" in prompt
    assert "建议讲解风格：step_by_step" in prompt
    assert "不生成整章摘要" in prompt
    assert "适用条件和变量含义" in prompt
    assert "source_citation_ids 必须使用下方 chunk_id，数量为 1-4 个" in prompt
    assert "学生导出讲义不会逐节展示 citation" in prompt
    assert "正文不要写“来源如下”“引用如下”" in prompt


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
