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


def _valid_handout_v2_payload() -> dict:
    return {
        "schema_version": 2,
        "title": "信道容量讲义",
        "overview": "围绕信道容量建立公式和直觉。",
        "difficulty": "medium",
        "estimated_minutes": 40,
        "learning_objectives": ["区分 Nyquist 和 Shannon 公式"],
        "prerequisites": [],
        "sections": [
            {
                "id": "sec_1",
                "title": "Shannon 公式",
                "lead": "有噪声信道的容量由带宽和信噪比共同限制。",
                "source_citation_ids": ["chunk_1"],
                "blocks": [
                    {
                        "type": "formula",
                        "title": "Shannon 公式",
                        "latex": "C = W \\\\log_2(1 + S/N)",
                        "purpose": "计算理论最大数据率。",
                        "variables": [
                            {"symbol": "C", "meaning": "最大数据率", "unit": "bps"},
                            {"symbol": "W", "meaning": "带宽", "unit": "Hz"},
                        ],
                        "conditions": ["有噪声信道"],
                        "limitations": ["理论上限"],
                        "source_citation_ids": ["chunk_1"],
                    }
                ],
                "key_points": ["不要把 dB 直接代入 S/N。"],
                "sort_order": 1,
            }
        ],
        "knowledge_map": {
            "type": "mindmap",
            "title": "关系图",
            "root": {"label": "信道容量", "children": []},
            "source_citation_ids": ["chunk_1"],
        },
        "formula_cards": [],
        "exam_focus": [],
        "self_check": [],
        "summary": "按条件选公式。",
    }


def test_handout_content_v2_accepts_structured_formula_and_mindmap_blocks() -> None:
    content = HandoutContent.model_validate(_valid_handout_v2_payload())

    assert content.schema_version == 2
    assert content.title == "信道容量讲义"
    assert content.sections[0].blocks[0].type == "formula"
    assert content.knowledge_map.type == "mindmap"


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
            "content_depth": "detailed",
            "example_intensity": "high",
            "assessment_intensity": "high",
            "review_intensity": "standard",
            "course_name": "计算机网络",
            "task_title": "物理层核心概念",
            "subtask_title": "物理层概念与通信基础",
            "subtask_type": "learn",
            "subtask_description": "理解物理层基本概念和通信模型。",
            "estimated_minutes": 45,
            "plan_goal": "两天内深度学习计算机网络物理层。",
            "diagnostic_foundation_needed": True,
            "diagnostic_weak_area": "calculation",
            "diagnostic_weak_topics": ["Nyquist / Shannon 公式"],
            "diagnostic_note": "希望多讲公式怎么用。",
            "teaching_strategy_hint": "加强公式变量、单位、适用条件、代入步骤和计算例题。",
        },
    )

    prompt = provider.prompts[0]
    assert "课程名称：计算机网络" in prompt
    assert "一级任务标题：物理层核心概念" in prompt
    assert "当前二级任务标题：物理层概念与通信基础" in prompt
    assert "当前二级任务类型：learn" in prompt
    assert "当前二级任务描述：理解物理层基本概念和通信模型。" in prompt
    assert "预计学习时间：45 分钟" in prompt
    assert "内容深度：detailed" in prompt
    assert "例题强度：high" in prompt
    assert "测试强度：high" in prompt
    assert "复习强度：standard" in prompt
    assert "学习计划目标：两天内深度学习计算机网络物理层。" in prompt
    assert "诊断薄弱方向：calculation" in prompt
    assert "薄弱知识点：Nyquist / Shannon 公式" in prompt
    assert "诊断补充说明：希望多讲公式怎么用。" in prompt
    assert "教学策略提示：加强公式变量、单位、适用条件、代入步骤和计算例题。" in prompt
    assert "建议讲解风格" not in prompt
    assert "diagnostic_explanation_style" not in prompt
    assert "不生成整章摘要" in prompt
    assert "适用条件和变量含义" in prompt
    assert "source_citation_ids 必须使用下方 chunk_id，数量为 1-4 个" in prompt
    assert "学生导出讲义不会逐节展示 citation" in prompt
    assert "正文不要写“来源如下”“引用如下”" in prompt
    assert "你的任务不是简单总结资料" in prompt
    assert "不要输出完整 Markdown 文档" in prompt
    assert "不要输出 HTML" in prompt
    assert "只输出符合 HandoutContent schema 的 JSON 对象" in prompt
    assert "schema_version 必须为 2" in prompt
    assert "subtask_type=learn：优先讲清新知识" in prompt
    assert "subtask_type=review：优先帮助回顾和查漏" in prompt
    assert "weak_area=calculation：公式必须说明用途、变量、单位、适用条件、限制条件，并给出代入步骤" in prompt
    assert "数学公式必须放入 type=formula block" in prompt
    assert "对比内容必须放入 type=table block" in prompt
    assert "知识关系优先使用 knowledge_map 的 mindmap tree" in prompt
    assert "Chart 只在资料提供真实数值时生成，不得编造数据" in prompt
    assert "不生成 SVG" in prompt
    assert "每个 block 需要 source_citation_ids，必须来自输入 chunk_id" in prompt


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
