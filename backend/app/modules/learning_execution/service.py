from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.errors import CourseNexusError
from app.modules.learning_execution import repository
from app.modules.learning_execution.schemas import (
    ExecutionContextRead,
    ExecutionCourseRead,
    ExecutionMaterialRead,
    ExecutionPlanRead,
    ExecutionSubTaskRead,
    ExecutionTaskRead,
)
from app.modules.study_plans.models import StudySubTask


VALID_TASK_STATUSES = {"not_started", "in_progress", "completed"}


def derive_task_status(subtask_statuses: list[str]) -> str:
    if not subtask_statuses or all(status == "not_started" for status in subtask_statuses):
        return "not_started"
    if all(status == "completed" for status in subtask_statuses):
        return "completed"
    return "in_progress"


def derive_plan_status(task_statuses: list[str]) -> str:
    if task_statuses and all(status == "completed" for status in task_statuses):
        return "completed"
    return "active"


def get_execution_context(db: Session, *, user_id: str, subtask_id: str) -> ExecutionContextRead:
    target = repository.get_execution_target(db, user_id=user_id, subtask_id=subtask_id)
    tasks = repository.list_tasks_for_plan_date(db, plan_id=target.plan.id, task_date=target.task.task_date)
    subtasks = repository.list_subtasks_for_tasks(db, task_ids=[task.id for task in tasks])
    subtasks_by_task: dict[str, list[StudySubTask]] = defaultdict(list)
    for subtask in subtasks:
        subtasks_by_task[subtask.task_id].append(subtask)

    return ExecutionContextRead(
        course=ExecutionCourseRead(course_id=target.course.id, name=target.course.name),
        plan=ExecutionPlanRead(plan_id=target.plan.id, title=target.plan.title, status=target.plan.status),
        execution_date=target.task.task_date,
        tasks=[
            ExecutionTaskRead(
                task_id=task.id,
                title=task.title,
                task_date=task.task_date,
                status=_as_task_status(task.status),
                sort_order=task.sort_order,
                subtasks=[_subtask_read(subtask) for subtask in subtasks_by_task[task.id]],
            )
            for task in tasks
        ],
        current_subtask_id=target.subtask.id,
        related_materials=_related_materials(db, user_id=user_id, course_id=target.course.id, subtask=target.subtask),
        handout_content_id=None,
        task_test_content_id=None,
    )


def _as_task_status(value: str) -> str:
    if value not in VALID_TASK_STATUSES:
        raise CourseNexusError(code="STATE_CONFLICT", message="任务状态不合法", status_code=409, details={"status": value})
    return value


def _subtask_read(subtask: StudySubTask) -> ExecutionSubTaskRead:
    return ExecutionSubTaskRead(
        subtask_id=subtask.id,
        title=subtask.title,
        subtask_type=subtask.subtask_type,
        description=subtask.description,
        status=_as_task_status(subtask.status),
        completed_at=subtask.completed_at,
        sort_order=subtask.sort_order,
    )


def _material_ids(subtask: StudySubTask) -> list[str]:
    raw = subtask.related_material_ids_json
    if raw is None:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise CourseNexusError(code="VALIDATION_ERROR", message="关联资料 ID 结构损坏", status_code=422)
    return list(dict.fromkeys(raw))


def _related_materials(db: Session, *, user_id: str, course_id: str, subtask: StudySubTask) -> list[ExecutionMaterialRead]:
    material_ids = _material_ids(subtask)
    materials = {material.id: material for material in repository.list_materials_by_ids(db, material_ids=material_ids)}
    reads: list[ExecutionMaterialRead] = []
    for material_id in material_ids:
        material = materials.get(material_id)
        if material is None:
            reads.append(ExecutionMaterialRead(material_id=material_id, name=None, material_type=None, parse_status=None, availability="deleted"))
            continue
        if material.user_id != user_id or material.course_id != course_id:
            raise CourseNexusError(code="STATE_CONFLICT", message="关联资料不属于当前课程", status_code=409, details={"material_id": material_id})
        availability = "deleted" if material.deleted_at is not None or material.parse_status == "deleted" else "available"
        reads.append(
            ExecutionMaterialRead(
                material_id=material.id,
                name=material.name,
                material_type=material.material_type,
                parse_status=material.parse_status,
                availability=availability,
            )
        )
    return reads