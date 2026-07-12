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
        if daily_minutes > preview.daily_available_minutes:
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
            "expected_material_ids: " + " ".join(sorted(expected_material_ids)),
            f"mapped_batches: {mapped_json}",
        ]
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
