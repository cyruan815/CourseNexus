from __future__ import annotations

import re
from typing import Any

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.handout.schemas import HandoutContent, HandoutGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextBatch, MaterialContextResult


_KNOWN_TERM_CORRECTIONS = {
    "Nyquest": "Nyquist",
    "Shanon": "Shannon",
    "bandwith": "bandwidth",
}


class HandoutGenerator:
    content_type = "handout"

    def __init__(self, model_provider: ModelProvider) -> None:
        self.model_provider = model_provider

    def generate(
        self,
        *,
        batches: tuple[MaterialContextBatch, ...],
        expected_material_ids: frozenset[str],
        parameters: dict[str, Any],
    ) -> GeneratorOutput:
        context = _context_from_batches(batches)
        _assert_material_coverage(context=context, expected_material_ids=expected_material_ids)
        params = HandoutGenerationParameters.model_validate(parameters)
        allowed_chunk_ids = {chunk.chunk_id for chunk in context.chunks}
        prompt = _build_prompt(context=context, params=params)
        content = self.model_provider.generate_structured(prompt=prompt, output_schema=HandoutContent)
        _assert_no_known_terminology_errors(content)
        item_citation_chunk_ids = _collect_item_citation_chunk_ids(content)
        citation_chunk_ids = {chunk_id for chunk_ids in item_citation_chunk_ids.values() for chunk_id in chunk_ids}
        if not citation_chunk_ids or not citation_chunk_ids.issubset(allowed_chunk_ids):
            raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="讲义引用不属于本次材料上下文", status_code=500)
        return GeneratorOutput(
            title="今日讲义",
            content_json=content.model_dump(mode="json"),
            item_citation_chunk_ids=item_citation_chunk_ids,
        )


def _assert_no_known_terminology_errors(content: HandoutContent) -> None:
    for text in _handout_text_fragments(content):
        for term, expected in _KNOWN_TERM_CORRECTIONS.items():
            if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                raise CourseNexusError(
                    code="GENERATION_SCHEMA_INVALID",
                    message="讲义包含明显术语错拼",
                    status_code=500,
                    details={"term": term, "expected": expected},
                )


def _handout_text_fragments(content: HandoutContent) -> list[str]:
    fragments: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                fragments.append(stripped)
            return
        if isinstance(value, dict):
            for item in value.values():
                collect(item)
            return
        if isinstance(value, list):
            for item in value:
                collect(item)

    collect(content.model_dump(mode="python"))
    return fragments


def build_generator(model_provider: ModelProvider) -> HandoutGenerator:
    return HandoutGenerator(model_provider=model_provider)


def _context_from_batches(batches: tuple[MaterialContextBatch, ...]) -> MaterialContextResult:
    chunks = [chunk for batch in batches for chunk in batch.chunks]
    return MaterialContextResult(chunks=chunks, no_parsed_material=not chunks)


def _assert_material_coverage(*, context: MaterialContextResult, expected_material_ids: frozenset[str]) -> None:
    represented_material_ids = {chunk.material_id for chunk in context.chunks}
    if represented_material_ids != set(expected_material_ids):
        raise CourseNexusError(
            code="MATERIAL_COVERAGE_INCOMPLETE",
            message="材料覆盖不完整",
            status_code=409,
            details={
                "expected_material_ids": sorted(expected_material_ids),
                "processed_material_ids": sorted(represented_material_ids),
            },
        )


def _build_prompt(*, context: MaterialContextResult, params: HandoutGenerationParameters) -> str:
    chunks = "\n\n".join(
        f"[chunk_id={chunk.chunk_id}; material={chunk.material_name}; page={_page_label(chunk)}]\n{chunk.content_text}"
        for chunk in context.chunks
    )
    task_context = "\n".join(_task_context_lines(params))
    role_and_task = "\n".join(
        [
            "你是一名擅长大学数学、物理、计算机和工程类课程的教学设计专家，也是 CourseNexus 的计划学习讲义生成器。",
            "你的任务不是简单总结资料，而是根据课程资料、学习目标、二级任务类型、学习时间和学生诊断，生成可在网页中稳定渲染的结构化个性化讲义。",
            "不要输出完整 Markdown 文档。",
            "不要输出 HTML。",
            "只输出符合 HandoutContent schema 的 JSON 对象。",
        ]
    )
    mode_rules = "\n".join(
        [
            "模式规则：",
            "- subtask_type=learn：优先讲清新知识，顺序为先说结论 -> 精确定义 -> 直觉理解 -> 为什么需要 -> 公式/步骤 -> 例子 -> 易错点。",
            "- subtask_type=review：优先帮助回顾和查漏，增加对比表、公式卡片、易错点、知识关系图和自测。",
            "- content_depth=concise：减少背景扩展，每个核心知识点保留定义、核心原理和至多 1 个基础例子。",
            "- content_depth=standard：完整解释定义、原理、例子、易错点，对核心公式给出必要推导。",
            "- content_depth=detailed：增加边界条件、反例、综合应用和容易被教材省略的中间步骤。",
            "- weak_area=calculation：公式必须说明用途、变量、单位、适用条件、限制条件，并给出代入步骤。",
            "- weak_area=concept：加强概念边界、直觉解释和相似概念对比。",
            "- weak_area=application：加强场景、输入输出、系统作用和迁移例题。",
            "- weak_area=memorization：加强核心结论卡片、易错判断和快速自测。",
        ]
    )
    planning_rules = "\n".join(
        [
            "生成前的内部处理：",
            "- 先在内部提取核心知识点、依赖关系、前置知识缺口、易混点、需要公式/图示/表格的位置；不要展示分析过程。",
            "- 区分必须掌握、理解即可和拓展内容，根据预计学习时间控制讲义长度。",
            "- 如果课程材料不足以支持某个结论，明确说明课程材料未提供足够信息，不要自行编造。",
            "- 只服务当前 subtask 的学习目标，不生成整章摘要或泛泛课程总结。",
        ]
    )
    schema_rules = "\n".join(
        [
            "输出 schema 要求：",
            "- schema_version 必须为 2。",
            "- sections[].blocks 是正文主体；不要把整节正文塞进一个 Markdown 字符串。",
            "- 每个 section 都围绕当前 subtask 展开，建议包含概念解释、为什么重要、易错点、公式 / 步骤 / 小例子。",
            "- learning_objectives 使用可观察动词，例如解释、区分、计算、推导、判断、比较、应用。",
            "- prerequisites 只补足理解当前任务所需的最小前置知识，不扩展成另一整章。",
        ]
    )
    block_rules = "\n".join(
        [
            "排版与块规则：",
            "- 数学公式必须放入 type=formula block，latex 必须是 KaTeX 兼容字符串，并写清适用条件和变量含义。",
            "- 对比内容必须放入 type=table block，最多 6 列、12 行。",
            "- 知识关系优先使用 knowledge_map 的 mindmap tree，不要把思维导图写成普通段落。",
            "- Mermaid 只用于流程、顺序或关系图；必须提供 title、code、explanation。",
            "- Chart 只在资料提供真实数值时生成，不得编造数据。",
            "- 不生成 SVG，除非输入资料明确要求且系统 schema 支持。",
            "- 每个 block 需要 source_citation_ids，必须来自输入 chunk_id。",
        ]
    )
    citation_rules = "\n".join(
        [
            "引用规则：",
            "- 每个 section 的 source_citation_ids 必须使用下方 chunk_id，数量为 1-4 个，且必须直接相关。",
            "- source_citation_ids 仅用于后端追溯和质量校验；学生导出讲义不会逐节展示 citation。",
            "- 正文不要写“来源如下”“引用如下”，也不要堆叠资料摘录。",
        ]
    )
    return "\n\n".join(
        [
            role_and_task,
            f"语言与强度：{params.language}；内容深度：{params.content_depth}；例题强度：{params.example_intensity}；测试强度：{params.assessment_intensity}；复习强度：{params.review_intensity}。",
            task_context,
            mode_rules,
            planning_rules,
            schema_rules,
            block_rules,
            citation_rules,
            f"资料片段：\n{chunks}",
        ]
    )


def _task_context_lines(params: HandoutGenerationParameters) -> list[str]:
    lines = [
        "任务上下文：",
        f"- 课程名称：{_context_value(params.course_name)}",
        f"- 学习计划目标：{_context_value(params.plan_goal)}",
        f"- 一级任务标题：{_context_value(params.task_title)}",
        f"- 当前二级任务标题：{_context_value(params.subtask_title)}",
        f"- 当前二级任务类型：{_context_value(params.subtask_type)}",
        f"- 当前二级任务描述：{_context_value(params.subtask_description)}",
        f"- 内容深度：{params.content_depth}",
        f"- 例题强度：{params.example_intensity}",
        f"- 测试强度：{params.assessment_intensity}",
        f"- 复习强度：{params.review_intensity}",
    ]
    if params.estimated_minutes is not None:
        lines.append(f"- 预计学习时间：{params.estimated_minutes} 分钟")
    if params.diagnostic_foundation_needed is not None:
        lines.append(f"- 是否需要补基础：{'是' if params.diagnostic_foundation_needed else '否'}")
    if params.diagnostic_weak_area:
        lines.append(f"- 诊断薄弱方向：{params.diagnostic_weak_area}")
    if params.diagnostic_weak_topics:
        lines.append(f"- 薄弱知识点：{'、'.join(params.diagnostic_weak_topics)}")
    if params.diagnostic_note:
        lines.append(f"- 诊断补充说明：{params.diagnostic_note}")
    if params.teaching_strategy_hint:
        lines.append(f"- 教学策略提示：{params.teaching_strategy_hint}")
    return lines


def _context_value(value: str | None) -> str:
    stripped = value.strip() if isinstance(value, str) else ""
    return stripped or "未提供"


def _collect_item_citation_chunk_ids(content: HandoutContent) -> dict[str, list[str]]:
    content_data = content.model_dump(mode="json")
    bindings: dict[str, list[str]] = {}
    section_chunk_ids: list[str] = []
    for section in sorted(content.sections, key=lambda item: item.sort_order):
        section_data = section.model_dump(mode="json")
        chunk_ids = _collect_source_citation_ids(section_data)
        bindings[section.id] = chunk_ids
        for chunk_id in chunk_ids:
            if chunk_id not in section_chunk_ids:
                section_chunk_ids.append(chunk_id)

    extra_chunk_ids = [
        chunk_id for chunk_id in _collect_source_citation_ids(content_data) if chunk_id not in section_chunk_ids
    ]
    if extra_chunk_ids:
        bindings["__handout__"] = extra_chunk_ids
    return {item_id: chunk_ids for item_id, chunk_ids in bindings.items() if chunk_ids}


def _collect_source_citation_ids(value: object) -> list[str]:
    chunk_ids: list[str] = []
    if isinstance(value, dict):
        source_ids = value.get("source_citation_ids")
        if isinstance(source_ids, list):
            for source_id in source_ids:
                if isinstance(source_id, str) and source_id.strip() and source_id not in chunk_ids:
                    chunk_ids.append(source_id)
        for child in value.values():
            for chunk_id in _collect_source_citation_ids(child):
                if chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)
    elif isinstance(value, list):
        for child in value:
            for chunk_id in _collect_source_citation_ids(child):
                if chunk_id not in chunk_ids:
                    chunk_ids.append(chunk_id)
    return chunk_ids


def _page_label(chunk: object) -> str | int | None:
    page = getattr(chunk, "page", None)
    if page is not None:
        return page
    return getattr(chunk, "page_index", None)
