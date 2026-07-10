from __future__ import annotations

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
) -> StudyPlanReduction:
    return model_provider.generate_structured(
        prompt=_build_reduce_prompt(
            mapped_batches=mapped_batches,
            payload=payload,
            expected_material_ids=expected_material_ids,
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
    for task in preview.tasks:
        if task.task_date < preview.start_date or task.task_date > preview.end_date:
            raise _invalid_generation("计划任务日期超出请求范围")
        if not task.subtasks:
            raise _invalid_generation("每天至少需要一个二级任务")

        daily_minutes = sum(subtask.estimated_minutes for subtask in task.subtasks)
        if daily_minutes > preview.daily_available_minutes:
            raise _invalid_generation("每日任务时长超过用户可用时间")

        for index, subtask in enumerate(task.subtasks):
            if subtask.subtask_type not in allowed_types:
                raise _invalid_generation("二级任务类型无效")
            if subtask.subtask_type == "test" and index != len(task.subtasks) - 1:
                raise _invalid_generation("测试任务必须排在当天最后")
            related_material_ids = set(subtask.related_material_ids)
            if not related_material_ids:
                raise _invalid_generation("二级任务必须关联资料")
            if not related_material_ids.issubset(scoped_material_ids):
                raise _invalid_generation("二级任务关联了范围外资料")


def _build_map_prompt(*, batch: MaterialContextBatch, payload: StudyPlanBuildRequest) -> str:
    chunk_lines = [
        f"chunk_id={chunk.chunk_id} material_id={chunk.material_id} heading={chunk.heading or ''} text={chunk.content_text}"
        for chunk in batch.chunks
    ]
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划材料分析器。",
            "请把本批资料提炼为可排入学习计划的知识单元。",
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {payload.daily_available_minutes}",
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
) -> str:
    mapped_json = [batch.model_dump(mode="json") for batch in mapped_batches]
    return "\n".join(
        [
            "你是 CourseNexus 的学习计划排程器。",
            "请把所有材料单元归并为日期连续、可执行的单课程学习计划预览。",
            f"goal_text: {payload.goal_text}",
            f"date_range: {payload.start_date.isoformat()} to {payload.end_date.isoformat()}",
            f"daily_available_minutes: {payload.daily_available_minutes}",
            "expected_material_ids: " + " ".join(sorted(expected_material_ids)),
            f"mapped_batches: {mapped_json}",
        ]
    )


def _invalid_generation(message: str) -> CourseNexusError:
    return CourseNexusError(code="GENERATION_SCHEMA_INVALID", message=message, status_code=500)