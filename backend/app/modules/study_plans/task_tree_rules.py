from __future__ import annotations

from collections.abc import Callable

from app.core.errors import CourseNexusError
from app.modules.study_plans.schemas import StudySubTaskPreview, StudyTaskPreview


_ASSESSMENT_TYPES = {"quiz", "test"}


def is_assessment_subtask(subtask: StudySubTaskPreview) -> bool:
    return subtask.subtask_type in _ASSESSMENT_TYPES


def validate_daily_assessment_contract(
    tasks: list[StudyTaskPreview],
    *,
    make_error: Callable[[str, dict[str, object] | None], CourseNexusError] | None = None,
) -> None:
    if not tasks:
        return

    error_factory = make_error or _generation_schema_error
    final_task_date = max(task.task_date for task in tasks)
    full_plan_material_ids: set[str] = set()
    full_plan_chunk_ids: set[str] = set()
    for task in tasks:
        for subtask in task.subtasks:
            if is_assessment_subtask(subtask):
                continue
            full_plan_material_ids.update(subtask.related_material_ids)
            full_plan_chunk_ids.update(subtask.citation_chunk_ids)

    for task in tasks:
        assessments = [subtask for subtask in task.subtasks if is_assessment_subtask(subtask)]
        if len(assessments) != 1:
            raise error_factory(
                "每天必须包含且只包含一个测试任务",
                {"task_sort_order": task.sort_order, "assessment_count": len(assessments)},
            )

        assessment = assessments[0]
        if not task.subtasks or task.subtasks[-1] is not assessment:
            raise error_factory(
                "自测任务必须排在当天最后",
                {"task_sort_order": task.sort_order, "subtask_sort_order": assessment.sort_order},
            )

        if task.task_date == final_task_date:
            required_material_ids = full_plan_material_ids
            required_chunk_ids = full_plan_chunk_ids
            message = "最终综合测试必须覆盖全计划前置学习任务"
        else:
            required_material_ids = set()
            required_chunk_ids = set()
            for subtask in task.subtasks:
                if subtask is assessment:
                    break
                if is_assessment_subtask(subtask):
                    continue
                required_material_ids.update(subtask.related_material_ids)
                required_chunk_ids.update(subtask.citation_chunk_ids)
            message = "当日测试必须覆盖当天前置学习任务"

        missing_material_ids = sorted(required_material_ids - set(assessment.related_material_ids))
        missing_chunk_ids = sorted(required_chunk_ids - set(assessment.citation_chunk_ids))
        if missing_material_ids or missing_chunk_ids:
            raise error_factory(
                message,
                {
                    "task_sort_order": task.sort_order,
                    "subtask_sort_order": assessment.sort_order,
                    "missing_material_ids": missing_material_ids,
                    "missing_chunk_ids": missing_chunk_ids,
                },
            )


def _generation_schema_error(message: str, details: dict[str, object] | None) -> CourseNexusError:
    return CourseNexusError(code="GENERATION_SCHEMA_INVALID", message=message, status_code=500, details=details)
