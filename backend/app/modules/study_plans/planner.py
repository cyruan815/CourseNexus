from __future__ import annotations

from math import ceil

from app.core.errors import CourseNexusError
from app.integrations.model_provider.base import ModelProvider
from app.modules.material_context.schemas import MaterialContextBatch
from app.modules.study_plans.schemas import (
    PlanBatchExtraction,
    StudyPlanBuildRequest,
    StudyPlanCoverage,
    StudyPlanPreview,
    StudyPlanReduction,
)


_WEAK_AREA_STRATEGY_RULES = {
    "concept": "加强概念解释：先用通俗语言说清概念含义、边界、因果关系和易混点，再安排检查产出。",
    "calculation": "加强公式、步骤推导、计算练习：任务要写明公式含义、适用条件、推导或代入步骤，并安排计算练习。",
    "application": "加强例题和应用任务：用典型例题或真实应用场景引入，再要求学生迁移到新题或新场景。",
    "memorization": "加强重点记忆、回顾、检查：标出必记结论、易错点和复述或默写检查任务。",
    "other": "根据 diagnostic_note 和 weak_topics 调整讲解顺序和任务颗粒度。",
}

_EXPLANATION_STYLE_RULES = {
    "plain_language": "plain_language：任务描述风格要用通俗短句解释术语，避免只给结论。",
    "step_by_step": "step_by_step：任务描述风格要按含义 -> 条件 -> 步骤 -> 练习检查的顺序写。",
    "example_first": "example_first：任务描述风格要先给例题或场景，再抽象概念和规则。",
    "exam_focused": "exam_focused：任务描述风格要突出重点记忆、易错回顾和可检查产出。",
}


def _diagnostic_profile_prompt_lines(diagnostic_profile: dict[str, object]) -> list[str]:
    if not diagnostic_profile:
        return [
            "diagnostic_profile: none",
            "诊断生成策略：未提供学前诊断时，按 goal_text、preference、资料难度和每日时间生成。",
        ]

    foundation_needed = _diagnostic_bool(diagnostic_profile.get("foundation_needed"))
    weak_topics = _diagnostic_string_list(diagnostic_profile.get("weak_topics"))
    weak_area = _diagnostic_string(diagnostic_profile.get("weak_area"), default="other")
    explanation_style = _diagnostic_string(diagnostic_profile.get("explanation_style"), default="plain_language")
    prior_knowledge_level = _diagnostic_string(diagnostic_profile.get("prior_knowledge_level"), default="unknown")
    question_version = _diagnostic_string(diagnostic_profile.get("question_version"), default="unknown")
    diagnostic_note = _diagnostic_string(diagnostic_profile.get("diagnostic_note"), default="")
    weak_topics_value = ", ".join(weak_topics) if weak_topics else "none"

    lines = [
        "diagnostic_profile:",
        f"question_version: {question_version}",
        f"prior_knowledge_level: {prior_knowledge_level}",
        f"foundation_needed: {_format_prompt_bool(foundation_needed)}",
        f"weak_topics: {weak_topics_value}",
        f"weak_area: {weak_area}",
        f"explanation_style: {explanation_style}",
        "诊断生成策略：diagnostic_profile 是 planner 约束，不是仅用于 preview/save 追溯。",
    ]
    if diagnostic_note:
        lines.append(f"diagnostic_note: {diagnostic_note}")
    if foundation_needed:
        lines.append("foundation_needed=true 时：计划必须前置安排补基础任务，优先放在第一天或最早可行日期；因现有 schema 的 subtask_type 不新增 foundation，请用 learn/review 类型并在标题或 description 中写明“补基础”。")
    else:
        lines.append("foundation_needed=false 时：不强制补基础，但仍要根据 weak_topics 调整顺序和粒度。")
    lines.extend(
        [
            "weak_topics 策略：weak_topics 对应主题必须更靠前、更细，能在任务标题、description 或排序中体现；不要只合并进泛泛章节。",
            f"weak_area 策略：{_WEAK_AREA_STRATEGY_RULES.get(weak_area, _WEAK_AREA_STRATEGY_RULES['other'])}",
            f"explanation_style 策略：{_EXPLANATION_STYLE_RULES.get(explanation_style, _EXPLANATION_STYLE_RULES['plain_language'])}",
        ]
    )
    return lines


def _diagnostic_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _format_prompt_bool(value: bool) -> str:
    return "true" if value else "false"


def _diagnostic_string(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _diagnostic_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item).strip())]


def map_material_batch(
    *,
    batch: MaterialContextBatch,
    payload: StudyPlanBuildRequest,
    model_provider: ModelProvider,
) -> PlanBatchExtraction:
    return model_provider.generate_structured(
        prompt=_build_map_prompt(batch=batch, payload=payload),
        output_schema=PlanBatchExtraction,
    )


def reduce_plan_batches(
    *,
    mapped_batches: list[PlanBatchExtraction],
    payload: StudyPlanBuildRequest,
    expected_material_ids: set[str],
    model_provider: ModelProvider,
    course_name: str | None = None,
) -> StudyPlanReduction:
    return model_provider.generate_structured(
        prompt=_build_reduce_prompt(
            mapped_batches=mapped_batches,
            payload=payload,
            expected_material_ids=expected_material_ids,
            course_name=course_name,
        ),
        output_schema=StudyPlanReduction,
    )


def make_coverage(*, expected_material_ids: set[str], processed_material_ids: set[str], batch_count: int) -> StudyPlanCoverage:
    return StudyPlanCoverage(
        expected_material_ids=sorted(expected_material_ids),
        processed_material_ids=sorted(processed_material_ids),
        batch_count=batch_count,
    )


def validate_preview(*, preview: StudyPlanPreview, scoped_material_ids: set[str]) -> None:
    allowed_types = {"learn", "review", "quiz", "test"}
    completion_quality_required = _requires_completion_quality(preview.goal_text)
    final_task_date = max((task.task_date for task in preview.tasks), default=preview.end_date)
    final_task_has_assessment = False

    for task in preview.tasks:
        if task.task_date < preview.start_date or task.task_date > preview.end_date:
            raise _invalid_generation("计划任务日期超出请求范围")
        if not task.subtasks:
            raise _invalid_generation("每天至少需要一个二级任务")

        daily_minutes = sum(subtask.estimated_minutes for subtask in task.subtasks)
        if daily_minutes > preview.daily_available_minutes and not _has_over_capacity_warning(preview):
            raise _invalid_generation("每日任务时长超过用户可用时间")
        if completion_quality_required and daily_minutes < _minimum_required_minutes(preview.daily_available_minutes):
            raise _invalid_generation("每日任务时长利用不足")

        for index, subtask in enumerate(task.subtasks):
            if subtask.subtask_type not in allowed_types:
                raise _invalid_generation("二级任务类型无效")
            if _is_assessment_type(subtask.subtask_type):
                if index != len(task.subtasks) - 1:
                    raise _invalid_generation("自测任务必须排在当天最后")
                if task.task_date == final_task_date:
                    final_task_has_assessment = True
            if not subtask.citation_chunk_ids:
                raise _invalid_generation("二级任务必须引用资料 chunk")
            related_material_ids = set(subtask.related_material_ids)
            if not related_material_ids:
                raise _invalid_generation("二级任务必须关联资料")
            if not related_material_ids.issubset(scoped_material_ids):
                raise _invalid_generation("二级任务关联了范围外资料")

    if completion_quality_required and not final_task_has_assessment:
        raise _invalid_generation("最后一天必须包含综合自测")


def _build_map_prompt(*, batch: MaterialContextBatch, payload: StudyPlanBuildRequest) -> str:
    daily_minutes = payload.daily_available_minutes if payload.daily_available_minutes is not None else "auto"
    chunk_lines = [
        (
            f"chunk_id={chunk.chunk_id} material_id={chunk.material_id} "
            f"page={chunk.page or ''} heading={chunk.heading or ''} text={chunk.content_text}"
        )
        for chunk in batch.chunks
    ]
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划材料分析器。",
            "请把本批资料提炼为可排入学习计划的知识单元。",
            "按 chunk 出现顺序、章节/页码顺序覆盖资料，不要只输出章节级摘要。",
            "把公式、标准、接口示例、典型设备、调制/编码/复用方法和安全隐患拆成可学习的细粒度知识点。",
            "每个有实质内容的 chunk 必须被至少一个知识单元引用，或在相邻知识单元 summary 中说明已合并。",
            "遇到 <!-- formula-not-decoded -->、图片、表格或图示缺失时，在 summary 中写明需人工复核。",
            "每个 PlanMaterialUnit 的 citation_chunk_ids 必须来自输入 chunk_id，不能留空。",
            "网络类资料要特别保留 10BaseT/RJ45、ASK、FSK、PSK、PCM、WDM、STDM、HUB、冲突域等具体术语。",
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {daily_minutes}",
            "material_ids: " + " ".join(batch.material_ids),
            "chunks:",
            *chunk_lines,
        ]
    )


def _build_reduce_prompt(
    *,
    mapped_batches: list[PlanBatchExtraction],
    payload: StudyPlanBuildRequest,
    expected_material_ids: set[str],
    course_name: str | None = None,
) -> str:
    mapped_json = [batch.model_dump(mode="json") for batch in mapped_batches]
    course_line = f"课程名称：{course_name}" if course_name else "课程名称：未提供，标题必须忠实使用 goal_text 中的课程名"
    diagnostic_prompt_lines = _diagnostic_profile_prompt_lines(payload.diagnostic_profile)
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划排程器。",
            "请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。",
            course_line,
            "标题必须使用课程名称的原文，不要改写、错写或自行造简称。",
            "如果目标包含“学完/掌握/精通/冲刺”等完成型意图，且材料足够，至少使用每日可用时间的 80%。",
            "学习任务时长不足时，用复习、练习、输出任务或自测补足，而不是留下大段空闲。",
            "所有 mapped units 都必须进入某个二级任务；可合并相近单元，但 description 里要说明覆盖内容。",
            "每天任务要具体可执行，包含可检查产出，例如公式默写、例题练习、对比表、错题回顾或口头复述。",
            "最后一天必须安排综合 quiz/test；quiz/test 必须是当天最后一个二级任务。",
            "每个 subtask 的 citation_chunk_ids 必须来自 mapped units，不能留空。",
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {payload.daily_available_minutes}",
            *diagnostic_prompt_lines,
            "expected_material_ids: " + " ".join(sorted(expected_material_ids)),
            f"mapped_batches: {mapped_json}",
        ]
    )


def _has_over_capacity_warning(preview: StudyPlanPreview) -> bool:
    warnings = preview.capacity.get("warnings")
    return (
        preview.capacity.get("feasibility_status") == "over_capacity"
        and isinstance(warnings, list)
        and "PLAN_OVER_CAPACITY" in warnings
    )


def _is_assessment_type(subtask_type: str) -> bool:
    return subtask_type in {"quiz", "test"}


def _requires_completion_quality(goal_text: str) -> bool:
    completion_keywords = ("学完", "掌握", "精通", "冲刺", "备考", "完成")
    return any(keyword in goal_text for keyword in completion_keywords)


def _minimum_required_minutes(daily_available_minutes: int) -> int:
    return ceil(daily_available_minutes * 0.6)


def _invalid_generation(message: str) -> CourseNexusError:
    return CourseNexusError(code="GENERATION_SCHEMA_INVALID", message=message, status_code=500)
