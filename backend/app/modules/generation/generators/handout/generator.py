from __future__ import annotations

import re
from typing import Any

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.generation.generators.handout.schemas import HandoutGenerationParameters
from app.modules.generation.orchestrator.contracts import GeneratorOutput
from app.modules.material_context.schemas import MaterialContextBatch, MaterialContextResult


_MERMAID_FENCE_PATTERN = re.compile(r"```mermaid\s*\n.*?\n```", flags=re.IGNORECASE | re.DOTALL)
_SVG_PATTERN = re.compile(r"<svg\b.*?</svg>", flags=re.IGNORECASE | re.DOTALL)

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
        title = _handout_title(params)
        prompt = _build_prompt(context=context, params=params, title=title)
        markdown = ""
        last_visual_error: CourseNexusError | None = None
        for attempt in range(2):
            current_prompt = prompt if attempt == 0 else _with_visual_retry_feedback(prompt)
            raw_markdown = self.model_provider.generate_text(prompt=current_prompt)
            markdown = ensure_handout_header(markdown=raw_markdown, title=title, source_note=params.source_note)
            if not markdown:
                raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="模型未返回可保存的 Markdown 讲义", status_code=500)
            _assert_no_known_terminology_errors(markdown)
            if _handout_has_visual(markdown):
                return GeneratorOutput(
                    title=title,
                    content=markdown,
                    content_json={"format": "markdown", "schema_version": 1},
                    item_citation_chunk_ids={},
                )
            last_visual_error = CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="讲义必须至少包含一张 SVG 或 Mermaid 图示",
                status_code=500,
            )

        if last_visual_error is not None:
            raise last_visual_error
        raise CourseNexusError(code="GENERATION_SCHEMA_INVALID", message="模型未返回可保存的 Markdown 讲义", status_code=500)


def _handout_has_visual(markdown: str) -> bool:
    return bool(_SVG_PATTERN.search(markdown) or _MERMAID_FENCE_PATTERN.search(markdown))


def _with_visual_retry_feedback(prompt: str) -> str:
    return "\n\n".join(
        [
            prompt,
            "Retry feedback: the previous handout was missing a required visual diagram. Return the full Markdown handout again and include at least one safe SVG diagram or Mermaid diagram that directly explains the most visual or conceptual part of this subtask.",
        ]
    )


def _assert_no_known_terminology_errors(markdown: str) -> None:
    for term, expected in _KNOWN_TERM_CORRECTIONS.items():
        if re.search(rf"\b{re.escape(term)}\b", markdown, flags=re.IGNORECASE):
            raise CourseNexusError(
                code="GENERATION_SCHEMA_INVALID",
                message="讲义包含明显术语错拼",
                status_code=500,
                details={"term": term, "expected": expected},
            )


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


def _build_prompt(*, context: MaterialContextResult, params: HandoutGenerationParameters, title: str) -> str:
    chunks = "\n\n".join(
        f"[chunk_id={chunk.chunk_id}; material={chunk.material_name}; page={_page_label(chunk)}]\n{chunk.content_text}"
        for chunk in context.chunks
    )
    task_context = "\n".join(_task_context_lines(params))
    role_and_task = "\n".join(
        [
            "你是一名擅长大学数学、物理、计算机和工程类课程的教学设计专家，也是 CourseNexus 的计划学习讲义生成器。",
            "请直接输出一份完整 Markdown 讲义，面向学生阅读和导出。",
            f"讲义标题必须是：{title}",
            "不要输出 JSON。",
            "不要输出 HTML callout 或非 SVG 原始 HTML；允许按图示规则输出安全 SVG。",
            "不要写 citation marker、source_citation_ids 或逐条资料来源注释。",
        ]
    )
    mode_rules = "\n".join(
        [
            "模式规则：",
            "- subtask_type=learn：优先讲清新知识，顺序为先说结论 -> 精确定义 -> 直觉理解 -> 为什么需要 -> 公式/步骤 -> 例子 -> 易错点。",
            "- subtask_type=review：优先帮助回顾和查漏，增加对比表、公式卡片、易错点和自测。",
            "- content_depth=concise：减少背景扩展，每个核心知识点保留定义、核心原理和至多 1 个基础例子。",
            "- content_depth=standard：完整解释定义、原理、例子、易错点，对核心公式给出必要推导。",
            "- content_depth=detailed：增加边界条件、反例、综合应用和容易被教材省略的中间步骤。",
            "- weak_area=calculation：公式必须说明用途、变量、单位、适用条件、限制条件，并给出代入步骤。",
            "- weak_area=concept：加强概念边界、直觉解释和相似概念对比。",
            "- weak_area=application：加强场景、输入输出、系统作用和迁移例题。",
            "- weak_area=memorization：加强核心结论卡片、易错判断和快速自测。",
        ]
    )
    source_note_rule = (
        f"- 一级标题下一段必须原样写入来源说明：{params.source_note}"
        if params.source_note
        else "- 一级标题下一段可以省略来源说明。"
    )
    markdown_rules = "\n".join(
        [
            "Markdown 输出要求：",
            "- 只输出 Markdown 正文，不要包裹 ```markdown 代码块。",
            "- 使用一个一级标题作为讲义标题。",
            source_note_rule,
            "- 使用二级/三级标题组织：概览、学习目标、正文、例题或公式、易错点、总结。",
            "- 行内公式只使用 $...$，例如：$C = B \\log_2(1 + S/N)$。",
            "- 块级公式只使用独立的 $$...$$，例如：$$\\nC = B \\log_2(1 + S/N)\\n$$。",
            "- 禁止使用 \\(...\\) 和 \\[...\\]。",
            "- 禁止用单独一行的 [ 和 ] 包裹公式。",
            "- 公式不要放进代码块。",
            "- Visual rule: every handout must include at least one visual diagram.",
            "- Use a visual diagram whenever a conceptual, structural, process, topology, encoding, signal, or comparison explanation would be easier to understand as a picture.",
            "- Use Mermaid mindmap for knowledge hierarchy, concept maps, and chapter/topic relationships.",
            "- Use Mermaid flowchart for procedures, system pipelines, state changes, and dependency chains.",
            "- Use safe SVG for spatial layouts, network topology, physical-layer workflows, signal waveforms, encoding examples, and diagrams that need precise node placement.",
            "- SVG may only use safe presentation elements such as svg, g, rect, line, path, circle, ellipse, polygon, polyline, text, tspan, defs, marker, title, and desc.",
            "- SVG may only use safe presentation attributes such as viewBox, x, y, cx, cy, r, width, height, fill, stroke, stroke-width, stroke-dasharray, text-anchor, dominant-baseline, transform, and marker-end.",
            "- SVG must not contain script, iframe, object, embed, foreignObject, style, onload, onclick, onerror, javascript:, data:, external images, external fonts, or external links.",
            "- Do not wrap SVG or Mermaid in HTML containers; output SVG directly or use a fenced ```mermaid code block.",
            "- 变量解释用普通 Markdown 列表，不要混进公式块。",
            "- 重要教学提示使用 GitHub alert 风格 blockquote，不要输出 HTML callout。",
            "- 支持的 callout 类型只有 NOTE、EXAMPLE、SUMMARY、WARNING、TIP。",
            "- 注意、补充说明、概念边界使用：> [!NOTE] 注意",
            "- 例题、应用题、计算题入口使用：> [!EXAMPLE] 例题 1",
            "- 核心结论、阶段总结使用：> [!SUMMARY] 核心结论",
            "- 易错点、常见误区、限制条件使用：> [!WARNING] 易错点",
            "- 解题提示、记忆提示、步骤提醒使用：> [!TIP] 解题提示",
            "- callout 正文每一行都必须继续以 > 开头。",
            "- 不要把整篇正文都写成 callout；只对需要强调的教学块使用 callout。",
            "- 普通解释仍使用段落、列表、表格和标题。",
            "- 输出前检查所有数学公式分隔符。",
            "- 对比内容使用 Markdown 表格。",
            "- 自测题或填空题的空格线使用全角低线，例如：＿＿＿＿；不要使用连续 ASCII 下划线 ______，避免 Markdown 渲染吞掉填空线。",
            "- 如果课程材料不足以支持某个结论，明确说明课程材料未提供足够信息，不要自行编造。",
            "- 只服务当前 subtask 的学习目标，不生成整章摘要或泛泛课程总结。",
        ]
    )
    return "\n\n".join(
        [
            role_and_task,
            f"语言与强度：{params.language}；内容深度：{params.content_depth}；例题强度：{params.example_intensity}；测试强度：{params.assessment_intensity}；复习强度：{params.review_intensity}。",
            task_context,
            mode_rules,
            markdown_rules,
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
    if params.source_note:
        lines.append(f"- 来源说明：{params.source_note}")
    return lines


def _handout_title(params: HandoutGenerationParameters) -> str:
    explicit_title = _context_value(params.handout_title)
    if explicit_title != "未提供":
        return explicit_title
    subtask_title = _context_value(params.subtask_title)
    if subtask_title != "未提供":
        return f"{subtask_title}讲义"
    return "讲义"


def _context_value(value: str | None) -> str:
    stripped = value.strip() if isinstance(value, str) else ""
    return stripped or "未提供"


def _normalize_markdown(value: str) -> str:
    markdown = value.strip()
    fence_match = re.fullmatch(r"```(?:markdown|md)?\s*\n(?P<body>.*?)\n```", markdown, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        markdown = fence_match.group("body").strip()
    return markdown


def ensure_handout_header(*, markdown: str, title: str, source_note: str | None) -> str:
    markdown = _normalize_markdown(markdown)
    if not markdown:
        return markdown
    note = source_note.strip() if isinstance(source_note, str) else ""
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        markdown = "\n".join(lines[1:]).strip()
    if note and markdown.startswith(note):
        markdown = markdown[len(note):].strip()
    return "\n\n".join(part for part in [f"# {title}", note, markdown] if part)


def _page_label(chunk: object) -> str | int | None:
    page = getattr(chunk, "page", None)
    if page is not None:
        return page
    return getattr(chunk, "page_index", None)
